# Solar Lovelace dashboard — rendered from stack.env (HA_ENTITY_SLUG)

title: Solar
views:
  - title: Production
    path: production
    icon: mdi:solar-power
    cards:
      - type: statistics-graph
        title: AC Power (7 days)
        entities:
          - sensor.${HA_ENTITY_SLUG}_solar_ac_power
        days_to_show: 7
        stat_types:
          - mean
          - max

      - type: gauge
        entity: sensor.solar_ac_power_display
        name: AC Output
        min: 0
        max: 300
        severity:
          green: 50
          yellow: 10
          red: 0

      - type: entities
        title: Live
        entities:
          - entity: sensor.${HA_ENTITY_SLUG}_solar_pv_power
            name: PV Power
          - entity: sensor.${HA_ENTITY_SLUG}_solar_grid_voltage
            name: Grid Voltage
          - entity: sensor.${HA_ENTITY_SLUG}_solar_grid_frequency
            name: Grid Frequency
          - entity: sensor.${HA_ENTITY_SLUG}_solar_inverter_temperature
            name: Temperature
          - entity: binary_sensor.${HA_ENTITY_SLUG}_solar_logger_online
            name: Device
          - entity: binary_sensor.${HA_ENTITY_SLUG}_solar_mqtt_bridge_online
            name: MQTT Bridge

      - type: entities
        title: Energy
        entities:
          - entity: sensor.solar_today_energy_computed
            name: Today (computed)
          - entity: sensor.${HA_ENTITY_SLUG}_solar_total_energy
            name: Lifetime

      - type: history-graph
        title: AC Power — live history
        hours_to_show: 48
        refresh_interval: 60
        entities:
          - entity: sensor.solar_ac_power_display
            name: AC Power (W)

      - type: statistics-graph
        title: Daily AC Energy (30 days)
        entities:
          - sensor.${HA_ENTITY_SLUG}_solar_total_energy
        days_to_show: 30
        stat_types:
          - change
        chart_type: bar

      - type: horizontal-stack
        cards:
          - type: button
            name: Export all solar data
            icon: mdi:download
            tap_action:
              action: call-service
              service: script.export_solar_csv
          - type: button
            name: Open History
            icon: mdi:chart-timeline-variant
            tap_action:
              action: url
              url_path: /history?entity_id=sensor.${HA_ENTITY_SLUG}_solar_ac_power,sensor.${HA_ENTITY_SLUG}_solar_pv_power,sensor.solar_today_energy_computed,sensor.${HA_ENTITY_SLUG}_solar_total_energy,sensor.${HA_ENTITY_SLUG}_solar_grid_voltage,sensor.${HA_ENTITY_SLUG}_solar_grid_frequency,sensor.${HA_ENTITY_SLUG}_solar_inverter_temperature

      - type: markdown
        content: >
          **Export:** runs a CSV dump of all recorder history for solar entities into
          `/config/exports/`. Download via **File editor** add-on, SFTP, or
          `docker cp homeassistant:/config/exports/ ./`
