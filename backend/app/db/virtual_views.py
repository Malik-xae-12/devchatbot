"""
Virtual views: view definitions we don't have CREATE VIEW permission for on
this DB, so instead of existing as real DB objects, they're inlined as a CTE
into every query that references them.

The SQL-generation prompt still tells the LLM about these exactly like any
other table/view (name + columns + description) — it references them the
normal way, e.g. `FROM vw_ProjectMemberBudgetFeatures`. The rewrite happens
transparently afterwards, in app/agents/query_rewriter.py, right before the
query hits the DB.

To add another one: drop its "CREATE OR ALTER VIEW x AS <body>" SQL below
with the CREATE/ALTER header stripped off (just the CTEs + final SELECT,
as one or more named CTEs), list its output columns, and register it here.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VirtualView:
    schema: str
    name: str
    description: str
    # One or more comma-separated CTE definitions, "name AS (...)", that
    # together produce a final CTE named exactly `name` — this is what gets
    # spliced into a generated query's WITH clause.
    cte_sql: str
    columns: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"


VIRTUAL_VIEWS: dict[str, VirtualView] = {
    "dbo.vw_ProjectMemberBudgetFeatures": VirtualView(
        schema="dbo",
        name="vw_ProjectMemberBudgetFeatures",
        description=(
            "One row per project + budget + assigned member, pre-joined and "
            "de-duplicated (Project, ProjectType, Customer, ProjectBudget, "
            "TTBillingType, ProjectMember, AppUser, TTBudgetAssignment). Includes "
            "derived fields: BudgetRemainingHrs, BudgetUtilizationPct, "
            "IsBudgetOverrun, MemberRemainingHrs, MemberUtilizationPct, "
            "IsMemberOverAssigned. Prefer this view over joining the base tables "
            "directly for any question about budget usage, hours remaining, "
            "utilization %, or overrun/over-assignment at the project or member "
            "level.\n"
            "NOTE: this is not a real DB view (no CREATE VIEW permission on this "
            "DB) — it is inlined as a CTE automatically, so query it exactly like "
            "any other table/view."
        ),
        columns=[
            "ProjectID", "ProjectName", "ProjectDescription", "ProjectTypeID",
            "ProjectTypeName", "ProjectIsActive", "ProjectManagerID",
            "ProjectManagerName", "ProjectCreatedDate",
            "CustomerID", "CustomerName", "CustomerCountry",
            "ProjectBudgetID", "BudgetName", "BudgetStartDate", "BudgetEndDate",
            "BudgetIsRecurring", "BudgetPOHrs", "BudgetOpeningBalanceHrs",
            "BudgetUsedHrs", "BudgetRemainingHrs", "BudgetUtilizationPct",
            "IsBudgetOverrun",
            "BillingTypeID", "BillingTypeName",
            "AppUserID", "MemberName", "MemberEmail", "MemberRoleID",
            "MemberIsActiveOnProject", "MemberDeactivatedDate",
            "MemberAssignedHrs", "MemberUsedHrs", "MemberMaxHrs",
            "MemberRemainingHrs", "MemberUtilizationPct", "IsMemberOverAssigned",
            "MemberHoursLastUpdated",
        ],
        cte_sql="""\
TTBudgetAssignmentDedup AS (
    SELECT
        TTBA.*,
        ROW_NUMBER() OVER (
            PARTITION BY TTBA.ProjectBudgetID, TTBA.AppUserID
            ORDER BY TTBA.UpdatedDate DESC, TTBA.ID DESC
        ) AS rn
    FROM TTBudgetAssignment TTBA
    WHERE TTBA.IsActive = 1
),
vw_ProjectMemberBudgetFeatures AS (
    SELECT
        P.ID                                        AS ProjectID,
        P.Name                                       AS ProjectName,
        P.Description                                AS ProjectDescription,
        P.ProjectTypeID,
        PT.Name                                       AS ProjectTypeName,
        P.IsActive                                    AS ProjectIsActive,
        P.ProjectManagerID,
        PM_MGR.FirstName + ' ' + PM_MGR.LastName       AS ProjectManagerName,
        P.CreatedDate                                  AS ProjectCreatedDate,
        C.ID                                        AS CustomerID,
        C.Name                                       AS CustomerName,
        C.Country                                    AS CustomerCountry,
        PB.ID                                       AS ProjectBudgetID,
        PB.Name                                      AS BudgetName,
        PB.StartDate                                  AS BudgetStartDate,
        PB.EndDate                                    AS BudgetEndDate,
        PB.IsRecurring                                AS BudgetIsRecurring,
        PB.POHrs                                      AS BudgetPOHrs,
        PB.OpeningBalanceHrs                          AS BudgetOpeningBalanceHrs,
        PB.UsedHrs                                    AS BudgetUsedHrs,
        ISNULL(PB.POHrs, 0) - ISNULL(PB.UsedHrs, 0)    AS BudgetRemainingHrs,
        CASE
            WHEN ISNULL(PB.POHrs, 0) = 0 THEN NULL
            ELSE ROUND(100.0 * ISNULL(PB.UsedHrs, 0) / PB.POHrs, 1)
        END                                             AS BudgetUtilizationPct,
        CASE
            WHEN PB.POHrs IS NOT NULL AND ISNULL(PB.UsedHrs, 0) > PB.POHrs THEN 1
            ELSE 0
        END                                             AS IsBudgetOverrun,
        TTBT.ID                                     AS BillingTypeID,
        TTBT.Name                                    AS BillingTypeName,
        PM.AppUserID,
        AU.FirstName + ' ' + AU.LastName               AS MemberName,
        AU.Email                                       AS MemberEmail,
        PM.AppRoleID                                   AS MemberRoleID,
        PM.IsActive                                    AS MemberIsActiveOnProject,
        PM.DeactivatedDate                             AS MemberDeactivatedDate,
        TTBA.AssignedHrs                                AS MemberAssignedHrs,
        TTBA.Used                                        AS MemberUsedHrs,
        TTBA.MaxHrs                                       AS MemberMaxHrs,
        ISNULL(TTBA.AssignedHrs, 0) - ISNULL(TTBA.Used, 0) AS MemberRemainingHrs,
        CASE
            WHEN ISNULL(TTBA.AssignedHrs, 0) = 0 THEN NULL
            ELSE ROUND(100.0 * ISNULL(TTBA.Used, 0) / TTBA.AssignedHrs, 1)
        END                                               AS MemberUtilizationPct,
        CASE
            WHEN TTBA.AssignedHrs IS NOT NULL AND ISNULL(TTBA.Used, 0) > TTBA.AssignedHrs THEN 1
            ELSE 0
        END                                               AS IsMemberOverAssigned,
        TTBA.UpdatedDate                                  AS MemberHoursLastUpdated
    FROM Project P
    LEFT JOIN ProjectType PT       ON P.ProjectTypeID = PT.ID
    LEFT JOIN AppUser PM_MGR       ON P.ProjectManagerID = PM_MGR.ID
    LEFT JOIN Customer C           ON C.ID = P.CustomerID
    LEFT JOIN ProjectBudget PB     ON P.ID = PB.ProjectID
    LEFT JOIN TTBillingType TTBT   ON PB.TTBillingTypeID = TTBT.ID
    LEFT JOIN ProjectMember PM     ON P.ID = PM.ProjectID
    LEFT JOIN AppUser AU           ON PM.AppUserID = AU.ID
    LEFT JOIN TTBudgetAssignmentDedup TTBA
        ON TTBA.ProjectBudgetID = PB.ID
       AND TTBA.AppUserID = PM.AppUserID
       AND TTBA.rn = 1
)""",
    ),
}
