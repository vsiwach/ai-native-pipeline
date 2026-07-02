# SSO and SCIM
Source: https://docs.baseten.co/organization/sso-and-scim

Authenticate Baseten users through your identity provider and automatically provision accounts, directory groups, and roles.

Single sign-on (SSO) and System for Cross-domain Identity Management (SCIM) let your organization wire Baseten to your existing identity provider (IdP). SSO controls authentication (who can sign in). SCIM controls the identity lifecycle (who has an account, and what permissions they have once they sign in).

<Note>
  SSO and SCIM are available on the Enterprise plan.
</Note>

## How it works

### Single sign-on

When SSO is enabled, sign-ins are routed to a hosted login page that delegates authentication to your IdP and returns the user to Baseten on success.

You don't run anything on Baseten's side. Once your IdP connection is configured, Baseten reads the authenticated identity and either signs the user in or provisions a new user account on the fly.

### SCIM

When SCIM is enabled, Baseten receives directory changes from your IdP through WorkOS. When you change a user, group, or membership in your IdP, those changes flow to Baseten and typically appear within a minute.

Baseten mirrors your IdP groups as **directory groups**. Directory groups are read-only in Baseten: you can't add or remove members or rename a group from the Baseten console. All membership changes happen in your IdP.

## Supported identity providers

Baseten supports any SAML 2.0 IdP and any SCIM 2.0 directory provider through WorkOS, including:

* Okta
* Microsoft Entra ID (Azure AD)
* Google Workspace

For the full list and provider-specific setup steps, see the [WorkOS SSO docs](https://workos.com/docs/sso) and [WorkOS Directory Sync docs](https://workos.com/docs/directory-sync).

## Enable SSO and SCIM

To enable SSO and SCIM, [contact support](mailto:support@baseten.co) with:

* Your Baseten organization name.
* The email address of the person who configures SSO and Directory Sync (usually an IT admin).
* The email domain or domains your users sign in with.

Support sends you a one-time link to the WorkOS admin portal with step-by-step instructions for configuring SSO and SCIM in your IdP. Once both connections are verified, SSO is required for all sign-ins to your organization and your synced directory groups appear in the **Directory Groups** section of the **Members** tab in **Organization settings**.

<Note>
  We also support enabling SSO without SCIM.
</Note>

## Just-in-time provisioning

When a user signs in to Baseten through SSO for the first time, Baseten provisions a user account for them automatically, or **just-in-time**. Just-in-time provisioned users:

* Join your organization with the **Member** role.
* Are added to the [default team](/organization/teams) with the **Team Member** role.

If your organization has SCIM enabled, just-in-time provisioned users also:

* Join your organization with [effective permissions](#effective-permissions)
* Have their directory group memberships backfilled

Members can deploy and call models. They can't manage organization settings, billing, or other users.

To grant a user a different role or assign them to additional teams, an Organization Admin can update their assignments in **Organization settings** → **Members** after the first sign-in. Admins can also [invite](/organization/teams#invite-members-to-a-team) users directly to assign them specific roles in advance. The invitee still needs to sign in through SSO when opening the invite link.

## Assign roles to directory groups

With SCIM enabled, organization Admins can assign Baseten roles to directory groups. Group membership comes from your IdP; permissions are managed in Baseten.

To see your synced groups, navigate to **Organization settings** and select the **Members** tab. Your synced groups appear in the **Directory Groups** section, which shows each group's name, member count, assigned organization role, and last-synced timestamp.

### Organization roles

You can assign the organization Admin role to a directory group. The Member role is the default for any user who signs in through SSO and isn't granted the Admin role either directly or through a directory group.

To change a directory group's organization role:

1. Open **Organization settings** and select the **Members** tab.
2. In the **Directory Groups** section, find the group and select its role from the dropdown.
3. Choose **Admin** to grant organization-admin permissions to everyone in the group.

For what each organization role can do, see [Organization roles](/organization/teams#organization-roles).

### Team roles

If your organization has multiple teams enabled, an Organization or Team Admin can assign the **Team Admin** or **Team Member** role to a directory group, scoped to a specific team. Team-level group assignments apply only to that team. A user who belongs to multiple teams can have different team roles in each.

For the underlying role definitions, see [Team roles](/organization/teams#team-roles).

### Restricted environments

You can also grant directory groups access to [restricted environments](/organization/restricted-environments). See the restricted environments doc for the assignment flow.

### Effective permissions

A user's effective permissions are the union of their direct role assignments and the permissions inherited from every directory group they belong to. If any group grants a permission, the user has it; permissions can't be explicitly denied through groups. When a direct assignment and a group assignment grant different roles, the more-permissive role wins.

To audit where a user's permissions come from, select the user in **Organization settings** → **Members**. Each role is listed alongside its source, either a direct assignment or a specific directory group.

## Deprovisioning

To deprovision a user, an Organization Admin can delete them from the **Members** tab in **Organization settings**. Deletion revokes any logged-in sessions and personal API keys. Any service or pipeline that uses the user's personal API keys will no longer be able to authenticate.

If your organization has SCIM enabled, Baseten deprovisions users automatically based on changes in your IdP. When you delete a user from your IdP, mark them inactive, or remove them from every synced group, Baseten:

* Deactivates the user's Baseten account. The user can no longer sign in.
* Revokes every API key the user owns.

If you re-add the same user in your IdP later, Baseten restores their account along with their previous team memberships and roles. API keys aren't restored. The user needs to generate new keys after signing back in.

<Warning>
  If your CI/CD or production workloads depend on a personal API key, migrate them to a [team API key](/organization/api-keys) so that deprovisioning a user doesn't break your pipelines.
</Warning>

## Require group-based assignment for admin roles

With SCIM enabled, you can require that users only hold the organization Admin role through directory-group membership. This enforces just-in-time admin access: pair it with IdP features like Okta's time-boxed group memberships, and admins gain access when they need it and lose access when their IdP membership expires.

To enable this setting, navigate to **Organization settings**, select the **Members** tab, and select **Require group-based assignment for admin roles**. Before you can enable it, at least one directory group must already hold the Admin role.

When you enable the setting:

* Baseten converts every direct Admin to a Member.
* Admin access requires membership in a directory group with the Admin role assigned. Direct Admin assignment is blocked while the setting is enabled.

<Warning>
  Plan this change carefully. [Contact support](mailto:support@baseten.co) if you lose admin access and/or need to disable this requirement.
</Warning>

## Considerations

* SSO is enabled at the organization level. You can't selectively enable it for individual users or teams.
* Email domains must match the domains configured in your IdP connection. Users with email addresses outside your configured domains can't sign in through SSO.
* Directory groups are read-only in Baseten. Group membership changes happen in your IdP.
* To disable SSO or SCIM, [contact support](mailto:support@baseten.co). Disabling SCIM removes all directory groups and their role assignments from Baseten. User accounts and direct role assignments aren't affected.
