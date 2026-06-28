DOMAIN = "irbridge"

CONF_PROTOCOL = "protocol"
CONF_SENDER = "sender"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_TEXT_ENTITY_ID = "text_entity_id"
CONF_INFRARED_ENTITY_ID = "infrared_entity_id"
CONF_POWER_OFF_TUYA = "power_off_tuya"
CONF_POWER_ON_TUYA = "power_on_tuya"

PROTOCOL_MIDEA = "midea"
PROTOCOL_ELECTRA = "electra"
# PROTOCOLS is derived from the generator registry at runtime via generators.available_protocols()

SENDER_MQTT_TUYA = "mqtt_tuya"
SENDER_INFRARED_ENTITY = "infrared_entity"
SENDERS = [SENDER_MQTT_TUYA, SENDER_INFRARED_ENTITY]
