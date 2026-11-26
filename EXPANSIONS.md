# Optional documentation lookup

The meetings and tasks kit works without Context7. If your harness already has Context7 and you want technical documentation, explicitly opt into using it for that task. Otherwise use supplied docs or the vendor's official documentation. If you want to add Context7 yourself, review its [installation guide](https://github.com/upstash/context7) and choose the instructions for your harness. The kit does not install or configure it or edit harness settings.

For example, a pipeline plan can cover stages, dependencies, permissions, approvals, failure handling and verification from requirements and documentation. Mark account-specific details as assumptions for the owner to validate: actual permissions, quotas, resource names, and whether an execution succeeds. Finding AWS documentation is not an account check. The kit does not use AWS credentials, inspect accounts, run deployments or start background agents.
