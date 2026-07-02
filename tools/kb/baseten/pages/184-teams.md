# Teams
Source: https://docs.baseten.co/organization/teams

Organize your organization into multiple teams with isolated resources and granular access control.

Teams let you segment your Baseten organization into multiple isolated
groups, each with its own resources, members, and access controls. Use teams to
separate environments by function, project, or access level.

<Note>
  Teams are available for organizations on our Enterprise tier.
  [Contact us](mailto:support@baseten.co) to enable teams for your
  organization.
</Note>

## How teams work

Every organization has a **default team** that contains all existing resources.
In the single-team world, you work within this default team without seeing any
team-specific UI.

When teams are enabled, Organization Admins can create additional teams within the
organization. Each team operates as an isolated unit with its own:

* Models, Chains, and training projects
* Secrets
* Team-level API keys
* Restricted environments
* Team members and roles

Billing remains at the organization level. All teams within an organization
share the same billing account and usage tracking.

## Roles and permissions

Teams introduce a two-level role hierarchy:

* Organization roles
* Team roles

### Organization roles

Organization-level roles determine what a user can do across the entire organization:

| Permission                  | Admin | Member |
| :-------------------------- | ----- | ------ |
| Manage billing              | ✅     | ❌      |
| Manage teams                | ✅     | ❌      |
| Manage organization members | ✅     | ❌      |
| View all teams              | ✅     | ❌      |

Organization Admins have implicit admin-level access to all teams and all restricted environments.

### Team roles

Team-level roles determine what a user can do within a specific team:

| Permission                                   | Team Admin | Team Member |
| :------------------------------------------- | ---------- | ----------- |
| Manage team members                          | ✅          | ❌           |
| Create restricted environments               | ✅          | ❌           |
| Create team API keys                         | ✅          | ❌           |
| Deploy models, Chains, and training projects | ✅          | ✅           |
| Call models                                  | ✅          | ✅           |
| View team resources                          | ✅          | ✅           |

A user can have different roles in different teams. For example, a data scientist might be a Team Admin for the Research team where they run experiments, while having Team Member access to the Inference team to deploy trained models.

<Note>
  If your organization uses [SCIM](/organization/sso-and-scim#assign-roles-to-directory-groups), you can assign these roles to directory groups. Every user in a directory group inherits the group's roles automatically.
</Note>

## Manage teams

Organization Admins can create and delete teams. Team Admins can manage membership within their teams.

### Create a team

To create a team:

1. From the left navigation, select the dropdown next to the team name and select **Create new team**.
2. Enter a team name and optionally select an icon.
3. Choose **Create team**.

The default team cannot be deleted, but you can rename it.

### Invite members to a team

To invite a new member and add them to teams:

1. Navigate to **Organization settings** and select the **Members** tab.
2. Select **Invite member**.
3. Enter the member's email address.
4. Select the organization role: **Admin** or **Member**.
5. Select the teams to add them to.
6. For each team, set their team role: **Team Admin** or **Team Member**.
7. Select **Invite member**.

The invited user receives an email to join the organization and is automatically added to the selected teams with the specified roles.

To add an existing organization member to a team, navigate to the team's settings page, select the **Members** tab, and add them from there.

### Remove a member

To remove a member from the organization:

1. Navigate to **Organization settings** and select the **Members** tab.
2. Find the member you want to remove.
3. Select the trash icon next to their name.

Removing a member from the organization removes them from all teams.

To remove a member from a specific team without removing them from the organization, navigate to the team's settings page, select the **Members** tab, and remove them from there.

### Change a member's role

To change a member's organization or team roles:

1. Navigate to **Organization settings** and select the **Members** tab.
2. Select the pencil icon next to the member's name.
3. Update their organization role or team assignments as needed.
4. Select **Save changes**.

You can also change a member's team role from the team's settings page by navigating to the **Members** tab.

### Switch between teams

Use the team selector in the navigation to switch between teams.
The team selector displays all teams you have access to.
Selecting a team filters the view to show only that team's resources and settings.

## Team-scoped resources

### Secrets

Secrets are scoped to individual teams.
Each team maintains its own set of secrets, and models deployed to a team can only access that team's secrets.

To manage secrets for a team:

1. Switch to the team using the team selector in the navigation.
2. Navigate to **Settings** and select **Secrets**.
3. Add or modify secrets for that team.

For more information, see [Best practices for secrets](/organization/secrets).

### API keys

API keys can be personal or team-scoped:

* **Personal API keys** are tied to your user account and provide access to resources across all teams you belong to. Use personal keys for local development and testing.
* **Team API keys** are scoped to a single team and can only access that team's resources. Use team keys for automation and production deployments. Only Team Admins and organization Admins can create team API keys.

To create a team API key:

1. Navigate to **Settings** and select **API Keys**.
2. Select **Create API Key**.
3. Choose the team to scope the key to.
4. Name the key and select **Create**.

For more information, see [Best practices for API keys](/organization/api-keys).

### Restricted environments

Restricted environments work at the team level. When you create a restricted
environment, it applies to all models and Chains within that team.

For more information, see
[Restricted environments](/organization/restricted-environments).

## Deploy to a team

To deploy to a team, you can use the Truss CLI or the UI.

### Use the Truss CLI

To deploy a model to a specific team, use the `--team` flag with `truss push`:

```sh theme={"system"}
truss push --team your-team-name
```

If you omit the `--team` flag, Truss infers the target team using the following logic:

1. If you belong to only one team, Truss deploys to that team.
2. If a model with the same name exists in only one of your accessible teams, Truss deploys to that team.
3. If there is ambiguity (for example, the same model name exists in multiple teams), Truss prompts you to select a team.

<Note>
  In non-interactive contexts (CI runners, scripts, agent shells, or any invocation with `--non-interactive`), Truss can't prompt. If you belong to multiple teams and rules 1 and 2 above leave the target team ambiguous, `truss push` fails with:

  ```
  Error: Team selection required but running in a non-interactive context. Pass --team <name> (available: ...).
  ```

  Pass `--team <name>` explicitly whenever you run `truss push` from automation. Requires Truss `0.18.3` or later.
</Note>

### Use the UI

The team selector determines which team a model belongs to when you create or deploy through the Baseten console.
To deploy to a specific team, switch to that team before creating or deploying resources.

## Considerations

### Model APIs

Model APIs are only available in the default team.
You can't create or access Model APIs from other teams.

### Billing

Billing is managed at the organization level.
There's no team-level billing breakdown or budget controls.
All usage across teams is aggregated in the organization's [billing and usage dashboard](/organization/billing), which is visible only to organization Admins.

### Resource naming

Model and Chain names must be unique within a team.
The same name can exist in different teams, but this may require explicit team specification when using the Truss CLI.

## Migrate to multiple teams

When teams are enabled for your organization, all existing resources remain in the default team.
You can then create additional teams and organize resources based on your needs.

Common team structures include:

* **By organizational structure**: Create teams for distinct departments or groups within your organization using Baseten. The recommended way to manage environments on Baseten is with [deployment environments](/deployment/environments), since this allows for centralized management, promotion workflows, and varying levels of access control.
* **By function**: Separate teams for different projects or use cases (for example, a training team and an inference team).
* **By access level**: Separate teams based on who should have access to modify production resources.

There is no single correct way to structure teams.
Consider your organization's access control needs, how you want to isolate secrets and credentials, and how different groups within your organization work with Baseten.

To move a model or Chain to a different team, redeploy it while switched to the target team. The original resource in the default team can then be deleted if no longer needed.
