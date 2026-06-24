from __future__ import annotations

import unittest
from types import SimpleNamespace

from web_agent_demo.simulation_engine import (
    SimulationControls,
    apply_dispatch_decision,
    advance_simulation,
    create_simulation_session,
    simulation_to_dict,
)


class DeliverySimulationEngineTest(unittest.TestCase):
    def test_same_seed_creates_reproducible_initial_world(self):
        controls = SimulationControls(courier_count=7, order_intensity=0.5, burstiness=0.4, weather="clear", congestion_level=0.3)

        left = create_simulation_session("commerce_peak", seed="stable-seed", controls=controls)
        right = create_simulation_session("commerce_peak", seed="stable-seed", controls=controls)

        self.assertEqual(left.session.session_id, right.session.session_id)
        self.assertEqual(simulation_to_dict(left.tick), simulation_to_dict(right.tick))
        self.assertEqual(len(left.tick.couriers), 7)
        self.assertEqual(len(left.tick.merchants), 6)
        self.assertEqual(left.tick.orders, ())

    def test_couriers_move_when_time_advances(self):
        start = create_simulation_session("commerce_peak", seed="move-seed", controls=SimulationControls(courier_count=5))
        before = {courier.id: (courier.position.lat, courier.position.lng) for courier in start.tick.couriers}

        advanced = advance_simulation(start.session, start.tick, advance_seconds=20)
        after = {courier.id: (courier.position.lat, courier.position.lng) for courier in advanced.tick.couriers}

        moved = [courier_id for courier_id, position in before.items() if after[courier_id] != position]
        self.assertGreaterEqual(len(moved), 1)
        self.assertIn("courier_moved", {event.event_type for event in advanced.timeline_delta})
        self.assertEqual(advanced.tick.sim_time_s, 20.0)

    def test_order_events_are_generated_by_time_and_burst(self):
        start = create_simulation_session(
            "commerce_peak",
            seed="orders-seed",
            controls=SimulationControls(courier_count=8, order_intensity=0.75, burstiness=0.75),
        )

        first = advance_simulation(start.session, start.tick, advance_seconds=20)
        second = advance_simulation(start.session, first.tick, advance_seconds=40)

        self.assertGreaterEqual(len(first.tick.orders), 1)
        self.assertIn("order_created", {event.event_type for event in first.timeline_delta})
        self.assertIn("order_burst", {event.event_type for event in second.timeline_delta})
        self.assertIsNotNone(second.compare_trigger)
        self.assertEqual(second.compare_trigger.reason, "order_burst")
        self.assertGreater(len(second.compare_trigger.active_order_ids), len(first.tick.active_order_ids))
        self.assertTrue(all(order.candidate_courier_ids for order in second.tick.orders))

    def test_controls_affect_courier_count_weather_and_traffic(self):
        rainy = create_simulation_session(
            "rain_low_willingness",
            seed="rain-seed",
            controls=SimulationControls(courier_count=4, weather="rain", congestion_level=0.9, order_intensity=0.4),
        )
        clear = create_simulation_session(
            "rain_low_willingness",
            seed="rain-seed",
            controls=SimulationControls(courier_count=4, weather="clear", congestion_level=0.1, order_intensity=0.4),
        )

        self.assertEqual(len(rainy.tick.couriers), 4)
        self.assertEqual(rainy.tick.map_state["weather"], "rain")
        self.assertGreater(rainy.tick.traffic_state["congestion_level"], clear.tick.traffic_state["congestion_level"])
        self.assertLess(
            sum(courier.speed_mps for courier in rainy.tick.couriers),
            sum(courier.speed_mps for courier in clear.tick.couriers),
        )

    def test_controls_patch_can_resize_courier_fleet_during_advance(self):
        start = create_simulation_session("scarce_repair", seed="resize-seed", controls=SimulationControls(courier_count=3))

        advanced = advance_simulation(start.session, start.tick, advance_seconds=20, controls_patch={"courier_count": 6})

        self.assertEqual(len(advanced.tick.couriers), 6)
        self.assertEqual([courier.id for courier in advanced.tick.couriers[-3:]], ["R004", "R005", "R006"])
        self.assertIn("fleet_resized", {event.event_type for event in advanced.timeline_delta})
        self.assertTrue(all(order.candidate_courier_ids for order in advanced.tick.orders))

    def test_dispatch_decision_updates_world_and_releases_courier_after_eta(self):
        start = create_simulation_session("commerce_peak", seed="dispatch-loop", controls=SimulationControls(courier_count=4))
        advanced = advance_simulation(start.session, start.tick, advance_seconds=60)
        order_id = advanced.tick.active_order_ids[0]
        order = next(item for item in advanced.tick.orders if item.id == order_id)
        courier_id = advanced.tick.couriers[0].id

        applied_tick, dispatch_events = apply_dispatch_decision(
            start.session,
            advanced.tick,
            (
                SimpleNamespace(
                    order_id=order_id,
                    courier_id=courier_id,
                    merchant_id=order.merchant_id,
                    eta_s=90.0,
                    delivery_eta_s=45.0,
                ),
            ),
        )
        dispatched_order = next(item for item in applied_tick.orders if item.id == order_id)
        dispatched_courier = next(item for item in applied_tick.couriers if item.id == courier_id)

        self.assertEqual(dispatched_order.status, "assigned")
        self.assertNotIn(order_id, applied_tick.active_order_ids)
        self.assertEqual(dispatched_courier.status, "delivering")
        self.assertEqual(dispatched_courier.current_order_ids, (order_id,))
        self.assertIn("dispatch_applied", {event.event_type for event in dispatch_events})

        settled = advance_simulation(start.session, applied_tick, advance_seconds=120, compare_if_due=False)
        delivered_order = next(item for item in settled.tick.orders if item.id == order_id)
        released_courier = next(item for item in settled.tick.couriers if item.id == courier_id)

        self.assertEqual(delivered_order.status, "delivered")
        self.assertEqual(released_courier.status, "idle")
        self.assertEqual(released_courier.current_order_ids, ())
        self.assertIn("orders_delivered", {event.event_type for event in settled.timeline_delta})


if __name__ == "__main__":
    unittest.main()
