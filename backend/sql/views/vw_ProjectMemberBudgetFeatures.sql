-- Deploy this on the on-prem SQL Server (in the DB pointed to by DB_NAME).
-- The schema_catalog picks this view up automatically via INFORMATION_SCHEMA
-- once it exists (VIEW rows are included alongside BASE TABLE rows), and
-- app/db/schema_catalog.py:KNOWN_DESCRIPTIONS carries the business-context
-- blurb the table-selector agent uses to prefer this view over the raw
-- Project/ProjectBudget/TTBudgetAssignment joins.

CREATE OR ALTER VIEW vw_ProjectMemberBudgetFeatures AS

WITH TTBudgetAssignmentDedup AS (
    -- Safety net: keep only one active row per (ProjectBudgetID, AppUserID)
    -- in case a member is ever reassigned/reactivated on the same budget.
    -- If your earlier check returned zero duplicate rows, this CTE is a
    -- no-op and simply passes every row through unchanged.
    SELECT
        TTBA.*,
        ROW_NUMBER() OVER (
            PARTITION BY TTBA.ProjectBudgetID, TTBA.AppUserID
            ORDER BY TTBA.UpdatedDate DESC, TTBA.ID DESC
        ) AS rn
    FROM TTBudgetAssignment TTBA
    WHERE TTBA.IsActive = 1
)

SELECT
    -- Project
    P.ID                                        AS ProjectID,
    P.Name                                       AS ProjectName,
    P.Description                                AS ProjectDescription,
    P.ProjectTypeID,
    PT.Name                                       AS ProjectTypeName,
    P.IsActive                                    AS ProjectIsActive,
    P.ProjectManagerID,
    PM_MGR.FirstName + ' ' + PM_MGR.LastName       AS ProjectManagerName,
    P.CreatedDate                                  AS ProjectCreatedDate,

    -- Customer
    C.ID                                        AS CustomerID,
    C.Name                                       AS CustomerName,
    C.Country                                    AS CustomerCountry,

    -- Budget
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

    -- Billing type
    TTBT.ID                                     AS BillingTypeID,
    TTBT.Name                                    AS BillingTypeName,

    -- Member
    PM.AppUserID,
    AU.FirstName + ' ' + AU.LastName               AS MemberName,
    AU.Email                                       AS MemberEmail,
    PM.AppRoleID                                   AS MemberRoleID,
    PM.IsActive                                    AS MemberIsActiveOnProject,
    PM.DeactivatedDate                             AS MemberDeactivatedDate,

    -- Member hours — TTBA.Used / AssignedHrs are already cumulative running
    -- totals per (ProjectBudgetID, AppUserID), so this is a direct
    -- passthrough, never a SUM/aggregation.
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
   AND TTBA.rn = 1;
