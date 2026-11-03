# Core package - platform kernel

## Modules
- `entities/kernel.py` - Dynamic entity system (schema-as-data)
- `workflows/engine.py` - Durable workflow engine invoking registered services
- `service_registry.py` - Anti-silo service registry
- `permissions.py` - RBAC permission model

## Design
Services register actions into `ServiceRegistry`. The `WorkflowEngine` invokes
those actions as workflow steps, threading outputs between steps. This makes
every service reachable from a workflow — no siloed services.
