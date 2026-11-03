# Templates Package

MJML email templates rendered by workflows before sending. Templates connect
to the engagement service through the ``ServiceRegistry`` so a workflow can
render a template and then send it via email/SMS/push in one durable pipeline.

## Templates

| Template | Used by workflow |
|----------|------------------|
| welcome | SaaS onboarding, marketing lead-nurture |
| win-back | Marketing campaign-win-back, SaaS churn-prevention |
| cart-abandonment | Ecommerce cart-abandonment |
| churn-prevention | SaaS churn-prevention |

## Usage

```python
from retention_analytics_templates.service import TemplateService

template_service = TemplateService(registry)
template_service.register()  # registers "templates.render" action
```

A workflow step can then call `templates.render` with a template name and
context variables, and pass the rendered HTML to `email.send`.
