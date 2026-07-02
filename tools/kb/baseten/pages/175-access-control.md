# Access control
Source: https://docs.baseten.co/organization/access

Manage access to your Baseten organization with role-based access control.

Baseten uses role-based access control (RBAC) to manage organization access.
Every organization member has one of two roles.

| Permission               | Admin | Member |
| :----------------------- | ----- | ------ |
| Manage members           | ✅     | ❌      |
| Manage billing           | ✅     | ❌      |
| Deploy models and Chains | ✅     | ✅      |
| Call models              | ✅     | ✅      |

**Admins** have full control over the organization, including member management and billing.
**Members** can deploy and call models but can't manage organization settings or other users.

<Note>
  If your organization uses multiple teams, see [Teams](/organization/teams) for information about team-level roles and permissions.
</Note>

If your organization uses [Single sign-on (SSO)](/organization/sso), users provisioned through your identity provider join with the **Member** role by default.

Role and membership changes are recorded in the [audit log](/organization/audit-logs).
