
MIN_SAFE_RESISTANCE_OHM = 100.0
LED_MIN_SERIES_RESISTANCE = 80.0


class Fault:
    def __init__(self, kind, component_ids, message):
        self.kind = kind
        self.component_ids = component_ids
        self.message = message

    def __repr__(self):
        return "Fault(%s, %s)" % (self.kind, self.message)


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


class ElectricalAnalyzer:
    def analyze(self, components, wire_pairs, board_pin_states, power_on):
        """
        components        - список объектов с атрибутами .instance_id,
                             .component_type, .pins (объекты с .pin_id),
                             .properties/.params (dict, напр. {'resistance': ...})
        wire_pairs         - список (pin_id_a, pin_id_b) - провода/соединения
                             free-node, объединяющие два пина в один net
        board_pin_states   - dict: канонический ключ пина платы ("13","A0","GND","5V",...)
                             -> {"role": "power"|"gnd"|"digital_high"|"digital_low"|"floating",
                                  "pin_id": "UNO:{i}"}
        power_on           - bool, подано ли питание (5V/VIN активны)
        """
        if not power_on:
            return []

        uf = UnionFind()
        for a, b in wire_pairs:
            uf.union(a, b)

        source_nets = set()
        ground_nets = set()
        for state in board_pin_states.values():
            pin_id = state["pin_id"]
            root = uf.find(pin_id)
            if state["role"] in ("power", "digital_high"):
                source_nets.add(root)
            elif state["role"] in ("gnd", "digital_low"):
                ground_nets.add(root)

        faults = []

        for root in source_nets & ground_nets:
            faults.append(Fault(
                "short",
                ["__net__"],
                "Короткое замыкание: цепь напрямую соединяет питание и GND без нагрузки.",
            ))

        for comp in components:
            if comp.component_type != "resistor" or len(comp.pins) < 2:
                continue
            resistance = float(_get_property(comp, "resistance", 1000))
            net_a = uf.find(comp.pins[0].pin_id)
            net_b = uf.find(comp.pins[1].pin_id)
            bridges = (net_a in source_nets and net_b in ground_nets) or \
                      (net_b in source_nets and net_a in ground_nets)
            if bridges and resistance < MIN_SAFE_RESISTANCE_OHM:
                faults.append(Fault(
                    "resistor_burn",
                    [comp.instance_id],
                    "Резистор перегорел: сопротивление %.0f Ом слишком мало для прямого "
                    "подключения между питанием и GND." % resistance,
                ))

        for comp in components:
            if comp.component_type != "led" or len(comp.pins) < 2:
                continue
            anode_pin, cathode_pin = comp.pins[0], comp.pins[1]
            anode_net = uf.find(anode_pin.pin_id)
            cathode_net = uf.find(cathode_pin.pin_id)

            if not (anode_net in source_nets and cathode_net in ground_nets):
                continue

            protected = False
            for other in components:
                if other.component_type != "resistor" or len(other.pins) < 2:
                    continue
                r_net_a = uf.find(other.pins[0].pin_id)
                r_net_b = uf.find(other.pins[1].pin_id)
                resistance = float(_get_property(other, "resistance", 1000))
                touches_led = anode_net in (r_net_a, r_net_b) or cathode_net in (r_net_a, r_net_b)
                if touches_led and resistance >= LED_MIN_SERIES_RESISTANCE:
                    protected = True
                    break

            if not protected:
                faults.append(Fault(
                    "led_burn",
                    [comp.instance_id],
                    "Светодиод сгорел: подключён напрямую между 5V/VIN и GND без "
                    "токоограничивающего резистора (>=%.0f Ом)." % LED_MIN_SERIES_RESISTANCE,
                ))

        return faults


def _get_property(component, key, default):
    props = getattr(component, "properties", None) or getattr(component, "params", None) or {}
    return props.get(key, default)
