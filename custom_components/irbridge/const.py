DOMAIN = "irbridge"

CONF_PROTOCOL = "protocol"
CONF_INFRARED_ENTITY_ID = "infrared_entity_id"

# Protocol names are not constants here on purpose: the generator registry
# in generators/__init__.py is the single source of truth, read at runtime
# through available_protocols().
