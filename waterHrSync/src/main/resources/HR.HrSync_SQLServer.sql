/* ===========================================================================
   HR.HrSync — MS SQL Server setup script
   Target DB : ecp_db
   NOTE: During development, source (KM_DEPT / KM_USER) and target
         (TsUser, TsDepartment …) share the same ecp_db.
         For production, create KM_DEPT / KM_USER in the separate HR source
         DB and point the "hrsource" datasource in datasource.xml to it.
   =========================================================================== */

USE [ecp_db]
GO

/* ===========================================================================
   1. HR source tables  (dev: same DB;  prod: create in HR source DB)
   =========================================================================== */

/* ----- KM_DEPT ------------------------------------------------------------ */
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = N'KM_DEPT')
BEGIN
    CREATE TABLE [dbo].[KM_DEPT] (
        [DEPARTMENTID] [nvarchar](20)  NOT NULL,   -- 單位代碼 (對應 DEPT_ANO)
        [DISPLAYNAME]  [nvarchar](250) NULL,        -- 單位名稱
        [BELONGTO]     [nvarchar](20)  NULL,        -- 上層單位代碼 (串接組織樹)
        CONSTRAINT [PK_KM_DEPT] PRIMARY KEY CLUSTERED ([DEPARTMENTID] ASC)
            WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF,
                  IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON,
                  ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
END
GO

/* ----- KM_USER ------------------------------------------------------------ */
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = N'KM_USER')
BEGIN
    CREATE TABLE [dbo].[KM_USER] (
        [EMPLOYEEID]   [nvarchar](20)  NOT NULL,   -- 員工編號 (唯一鍵)
        [DISPLAYNAME]  [nvarchar](100) NULL,        -- 員工姓名
        [EMAILADDRESS] [nvarchar](100) NULL,        -- 電子郵件信箱
        [LOGINID]      [nvarchar](100) NULL,        -- AD 登入帳號
        [DEPARTMENTID] [nvarchar](20)  NULL,        -- 所屬單位代碼 (關聯至 KM_DEPT)
        [ADSERVER]     [nvarchar](20)  NULL,        -- 網域驗證伺服器名稱
        [PASSWORD]     [varchar](1)    NOT NULL     -- 驗證狀態位元 (固定 '1')
            CONSTRAINT [DF_KM_USER_PASSWORD] DEFAULT ('1'),
        CONSTRAINT [PK_KM_USER] PRIMARY KEY CLUSTERED ([EMPLOYEEID] ASC)
            WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF,
                  IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON,
                  ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
END
GO

/* ===========================================================================
   2. Views  (ECP reads from these; swap underlying table/DB in production)
   =========================================================================== */

/* ----- v_KM_DEPT ---------------------------------------------------------- */
IF EXISTS (SELECT 1 FROM sys.views WHERE name = N'v_KM_DEPT')
    DROP VIEW [dbo].[v_KM_DEPT]
GO
CREATE VIEW [dbo].[v_KM_DEPT] AS
    SELECT
        [DEPARTMENTID],
        [DISPLAYNAME],
        [BELONGTO]
    FROM [dbo].[KM_DEPT]
GO

/* ----- v_KM_USER ---------------------------------------------------------- */
IF EXISTS (SELECT 1 FROM sys.views WHERE name = N'v_KM_USER')
    DROP VIEW [dbo].[v_KM_USER]
GO
CREATE VIEW [dbo].[v_KM_USER] AS
    SELECT
        [EMPLOYEEID],
        [DISPLAYNAME],
        [EMAILADDRESS],
        [LOGINID],
        [DEPARTMENTID],
        [ADSERVER],
        [PASSWORD]
    FROM [dbo].[KM_USER]
GO

/* ===========================================================================
   3. TsUnit — register HR.HrSync module with Quicksilver framework
   =========================================================================== */
IF NOT EXISTS (SELECT 1 FROM [dbo].[TsUnit] WHERE [FId] = '4806684c-e000-3135-6003-1961e9cb6d01')
BEGIN
    INSERT INTO [dbo].[TsUnit] (
        [FId],   [FCode],  [FName],  [FIcon],   [FBigIcon],
        [FEditId], [FModuleId],
        [FOpenMode], [FIsTreeStructure], [FIsTreeCheckPrivilege],
        [FIsSlaveUnit], [FSupportWorkflow], [FSupportUser],
        [FSupportDepartment], [FSupportAttachment], [FApiEnabled],
        [FTable], [FKeyField], [FKeyType], [FNameField],
        [FDataSource],
        [FHomeClassName],
        [FDaoClassName],
        [FServiceClassName],
        [FActionClassName],
        [FApiClassName]
    ) VALUES (
        '4806684c-e000-3135-6003-1961e9cb6d01',
        'HR.HrSync',
        N'人事系統同步',
        'quicksilver/image/unit/New.gif',
        'quicksilver/image/unit/New-64.png',
        '541c707d-79dd-4dbb-85fc-1a214fd5fce4',
        '21e2754a-d586-4bfa-bebe-768f70b9148b',
        'System', 0, 0,
        0, 0, 0,
        0, 0, 0,
        'TsUser', 'FId', 'Uuid', 'FName',
        'default',
        'com.ai3.ecp.cus.hrsync.HrSyncHome',
        'com.ai3.ecp.cus.hrsync.dao.impl.HrSyncDaoImpl',
        'com.ai3.ecp.cus.hrsync.service.impl.HrSyncServiceImpl',
        NULL,
        NULL
    )
END
GO

/* ===========================================================================
   4. TsTimer — setup in ecp 計時器
   =========================================================================== */

/* ===========================================================================
   5. Sample / test data  (remove before production deployment)
   =========================================================================== */

-- Departments
--   DEPARTMENTID / BELONGTO relationship mirrors the org tree.
--   During sync, depts with BELONGTO=NULL are parented to the root (集團,
--   FId = hrsync.TsDepartmentRootFId = 00000000-0000-0000-1001-000000000001).
--   '001001' = 總處  (root-level, BELONGTO=NULL)
--   '001002' = 資訊處 (child of 總處, triggers sysAdmin role)
--   '100001' = 其他處 (root-level, BELONGTO=NULL)
--   All departments in v_KM_DEPT are synced — there is no DEPARTMENTID filter.
IF NOT EXISTS (SELECT 1 FROM [dbo].[KM_DEPT] WHERE [DEPARTMENTID] = '001001')
BEGIN
    INSERT INTO [dbo].[KM_DEPT] ([DEPARTMENTID], [DISPLAYNAME], [BELONGTO]) VALUES
        ('001001', N'總處',   NULL),
        ('001002', N'資訊處', '001001'),
        ('100001', N'其他處', NULL)
END
GO

-- Employees
--   E001, E002 → 總處 general staff  (get default role only)
--   E003       → 資訊處 IT staff      (get default role + sysAdmin role)
--   E004       → 其他處               (now included — no DEPARTMENTID filter)
IF NOT EXISTS (SELECT 1 FROM [dbo].[KM_USER] WHERE [EMPLOYEEID] = 'E001')
BEGIN
    INSERT INTO [dbo].[KM_USER]
        ([EMPLOYEEID], [DISPLAYNAME],  [EMAILADDRESS],             [LOGINID],       [DEPARTMENTID], [ADSERVER], [PASSWORD])
    VALUES
        ('E001', N'張小明', 'zhang.xiaoming@example.com', 'zhang.xiaoming', '001001', 'AD01', '1'),
        ('E002', N'李小華', 'li.xiaohua@example.com',    'li.xiaohua',    '001001', 'AD01', '1'),
        ('E003', N'王資訊', 'wang.zixin@example.com',    'wang.zixin',    '001002', 'AD01', '1'),
        ('E004', N'趙其他', 'zhao.qita@example.com',     'zhao.qita',     '100001', 'AD01', '1')
END
GO