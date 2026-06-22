
import time

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.components_data import GND_PIN_KEYS, POWER_PIN_KEYS, uno_pin_index_by_key
from core.electrical_engine import ElectricalAnalyzer, UnionFind
from core.sketch_interpreter import Interpreter, SketchError, compile_sketch

TICK_MS = 30


class SimulationEngine(QObject):
    """Управляет питанием схемы и выполнением загруженного скетча."""

    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.pin_index = uno_pin_index_by_key()
        self.analyzer = ElectricalAnalyzer()

        self.power_on = False
        self.running = False

        self.pin_modes = {}
        self.digital_state = {}
        self.analog_pwm = {}
        self.tone_state = {}
        self.log_lines = []
        self._start_time = time.time()

        self.interpreter = None
        self._loop_gen = None
        self._pending_delay_ms = 0.0
        self._last_tick_time = None

        self.timer = QTimer()
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._tick)

        scene.on_power_requested = self.toggle_power
        scene.on_upload_requested = lambda: None

    def toggle_power(self):
        self.set_power(not self.power_on)

    def set_power(self, on):
        self.power_on = on
        self.scene.set_power(on)
        self.scene.power_button.set_active(on)
        if not on:
            self.stop()
            self._reset_component_visuals()
        self.refresh_visuals()
        self.status_changed.emit("Питание подано (5V)" if on else "Питание отключено")

    def upload_and_run(self, source_code):
        try:
            program = compile_sketch(source_code)
        except SketchError as exc:
            self.error_occurred.emit(str(exc))
            return False

        if not self.power_on:
            self.set_power(True)

        self.pin_modes.clear()
        self.digital_state.clear()
        self.analog_pwm.clear()
        self.tone_state.clear()
        self.log_lines.clear()
        self._start_time = time.time()

        self.interpreter = Interpreter(program, self)
        try:
            self.interpreter.run_setup()
        except SketchError as exc:
            self.error_occurred.emit(str(exc))
            self.interpreter = None
            return False

        self.running = True
        self.scene.simulation_running = True
        self.scene.upload_button.set_active(True)
        self._loop_gen = self.interpreter.run_loop_once()
        self._pending_delay_ms = 0.0
        self._last_tick_time = time.time()
        self.timer.start()
        self.status_changed.emit("Код загружен в микроконтроллер и выполняется")
        self.refresh_visuals()
        return True

    def stop(self):
        self.timer.stop()
        self.running = False
        self.scene.simulation_running = False
        self.scene.upload_button.set_active(False)
        self._loop_gen = None
        self.interpreter = None

    def _tick(self):
        now = time.time()
        elapsed_ms = (now - self._last_tick_time) * 1000.0 if self._last_tick_time else 0.0
        self._last_tick_time = now

        if self._pending_delay_ms > 0:
            self._pending_delay_ms -= elapsed_ms
            if self._pending_delay_ms > 0:
                return

        try:
            sent = None
            while True:
                item = self._loop_gen.send(sent)
                sent = None
                if isinstance(item, tuple) and item and item[0] == "delay":
                    self._pending_delay_ms = float(item[1])
                    break
        except StopIteration:
            self._loop_gen = self.interpreter.run_loop_once()
        except SketchError as exc:
            self.error_occurred.emit(str(exc))
            self.stop()
            return

        self.refresh_visuals()

    def pin_mode(self, pin, mode):
        self.pin_modes[str(pin)] = mode

    def digital_write(self, pin, val):
        self.digital_state[str(pin)] = 1 if val else 0
        self.tone_state.pop(str(pin), None)

    def digital_read(self, pin):
        return self._resolve_digital_read(str(pin))

    def analog_write(self, pin, val):
        self.analog_pwm[str(pin)] = max(0, min(255, int(val)))

    def analog_read(self, pin):
        return self._resolve_analog_read(str(pin))

    def tone(self, pin, freq):
        self.tone_state[str(pin)] = freq

    def no_tone(self, pin):
        self.tone_state.pop(str(pin), None)

    def millis(self):
        return int((time.time() - self._start_time) * 1000)

    def log(self, text):
        self.log_lines.append(text)
        self.status_changed.emit("Serial: %s" % text)

    def _build_unionfind(self):
        uf = UnionFind()
        for a, b in self.scene.wire_pairs():
            uf.union(a, b)
        for comp in self.scene.components:
            if comp.component_type == "button" and getattr(comp, "sim_pressed", False) and len(comp.pins) >= 4:
                uf.union(comp.pins[0].pin_id, comp.pins[2].pin_id)
                uf.union(comp.pins[1].pin_id, comp.pins[3].pin_id)
        return uf

    def _board_pin_id(self, key):
        idx = self.pin_index.get(str(key))
        return None if idx is None else "UNO:%d" % idx

    def _ids_for(self, keys):
        ids = []
        for k in keys:
            idx = self.pin_index.get(k)
            if idx is not None:
                ids.append("UNO:%d" % idx)
        return ids

    def _resolve_digital_read(self, key):
        if not self.power_on:
            return 0
        pin_id = self._board_pin_id(key)
        if pin_id is None:
            return 0
        uf = self._build_unionfind()
        net = uf.find(pin_id)
        grounded = any(uf.find(g) == net for g in self._ids_for(GND_PIN_KEYS))
        mode = self.pin_modes.get(str(key), 0)
        if mode == 2:
            return 0 if grounded else 1
        powered = any(uf.find(p) == net for p in self._ids_for(POWER_PIN_KEYS))
        return 1 if powered else 0

    def _resolve_analog_read(self, key):
        if not self.power_on:
            return 0
        pin_id = self._board_pin_id(key)
        if pin_id is None:
            return 0
        uf = self._build_unionfind()
        net = uf.find(pin_id)
        for comp in self.scene.components:
            if comp.component_type != "potentiometer" or len(comp.pins) < 2:
                continue
            wiper = comp.pins[1]
            if uf.find(wiper.pin_id) == net:
                angle = comp.params.get("angle", 270)
                ratio = max(0.0, min(1.0, (angle - 180.0) / 180.0))
                return int(ratio * 1023)
        return 0

    def refresh_visuals(self):
        uf = self._build_unionfind()
        gnd_ids = set(self._ids_for(GND_PIN_KEYS))
        power_ids = set(self._ids_for(POWER_PIN_KEYS)) if self.power_on else set()

        board_pin_states = {}
        for key, idx in self.pin_index.items():
            pin_id = "UNO:%d" % idx
            if pin_id in gnd_ids:
                role = "gnd"
            elif pin_id in power_ids:
                role = "power"
            elif self.pin_modes.get(key) == 1 and key in self.digital_state:
                role = "digital_high" if self.digital_state[key] else "digital_low"
            else:
                role = "floating"
            board_pin_states[key] = {"role": role, "pin_id": pin_id}

        for comp in self.scene.components:
            if comp.component_type == "led" and len(comp.pins) >= 2:
                comp.sim_led_lit = self.power_on and self._is_led_lit(comp, uf, gnd_ids)
                comp.update()
            elif comp.component_type == "buzzer" and len(comp.pins) >= 2:
                comp.sim_buzzer_active = self.power_on and self._is_buzzer_active(comp, uf, gnd_ids)
                comp.update()

        if self.power_on:
            faults = self.analyzer.analyze(self.scene.components, self.scene.wire_pairs(), board_pin_states, True)
            if faults:
                self.scene.apply_faults(faults)
                self.error_occurred.emit("; ".join(f.message for f in faults[:3]))

    def _is_led_lit(self, led, uf, gnd_ids):
        anode_net = uf.find(led.pins[0].pin_id)
        cathode_net = uf.find(led.pins[1].pin_id)
        cathode_grounded = any(uf.find(g) == cathode_net for g in gnd_ids)
        return cathode_grounded and self._net_is_hot(anode_net, uf)

    def _is_buzzer_active(self, buzzer, uf, gnd_ids):
        plus_net = uf.find(buzzer.pins[0].pin_id)
        minus_net = uf.find(buzzer.pins[1].pin_id)
        minus_grounded = any(uf.find(g) == minus_net for g in gnd_ids)
        if not minus_grounded:
            return False
        for key in self.tone_state:
            pid = self._board_pin_id(key)
            if pid and uf.find(pid) == plus_net:
                return True
        return self._net_is_hot(plus_net, uf)

    def _net_is_hot(self, net, uf):
        for pid in self._ids_for(POWER_PIN_KEYS):
            if uf.find(pid) == net:
                return True
        for key, val in self.digital_state.items():
            if val and self.pin_modes.get(key) == 1:
                pid = self._board_pin_id(key)
                if pid and uf.find(pid) == net:
                    return True
        for key, val in self.analog_pwm.items():
            if val > 0:
                pid = self._board_pin_id(key)
                if pid and uf.find(pid) == net:
                    return True
        return False

    def _reset_component_visuals(self):
        for comp in self.scene.components:
            comp.sim_led_lit = False
            comp.sim_buzzer_active = False
            comp.sim_pressed = False
            comp.update()
        self.scene.clear_faults()
