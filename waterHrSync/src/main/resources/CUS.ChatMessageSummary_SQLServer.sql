/* =====================================================
   TABLE
===================================================== */
CREATE TABLE TpCUSmChatMessageSummary
(
    FId uniqueidentifier PRIMARY KEY,
    FName varchar(50),
    U_RoomId varchar(50),
    U_ChatId varchar(50),
    U_UserId varchar(50),
    U_UserName varchar(50),
    U_AgentId varchar(50),
    U_SenderId varchar(50),
    U_SenderName varchar(50),
    U_SendTime datetime,
    U_Content varchar(max),
    U_Type varchar(20),
    U_AgentName varchar(50)
);
GO


/* =====================================================
   TsUnit
===================================================== */
INSERT INTO TsUnit (
    FId, FCode, FName, FIcon, FBigIcon, FEditId, FModuleId,
    FOpenMode, FIsTreeStructure, FIsTreeCheckPrivilege,
    FIsSlaveUnit, FSupportWorkflow, FSupportUser,
    FSupportDepartment, FSupportAttachment, FApiEnabled,
    FTable, FKeyField, FKeyType, FNameField
)
VALUES (
    '4806684c-e000-3135-6003-1961e9cb6d00',
    'CUS.ChatMessageSummary',
    N'聊天訊息彙整',
    'quicksilver/image/unit/New.gif',
    'quicksilver/image/unit/New-64.png',
    '541c707d-79dd-4dbb-85fc-1a214fd5fce4',
    '21e2754a-d586-4bfa-bebe-768f70b9148b',
    'System',0,0,
    0,0,0,
    0,0,1,
    'TpCUSmChatMessageSummary',
    'FId',
    'Uuid',
    'FName'
);
GO


/* =====================================================
   TsField（全部欄位）
===================================================== */
INSERT INTO TsField (FId,FUnitId,FName,FTitle,FType,FSize,FVisible)
VALUES
('4806684c-e000-3135-6003-1961e9cb7620','4806684c-e000-3135-6003-1961e9cb6d00','FId',N'ID','InputBox-Key',NULL,0),
('4806684c-e000-3135-6003-1961e9cb7650','4806684c-e000-3135-6003-1961e9cb6d00','FName',N'名稱','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961ea01bb80','4806684c-e000-3135-6003-1961e9cb6d00','U_AgentId','AgentId','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961ea475a80','4806684c-e000-3135-6003-1961e9cb6d00','U_AgentName','AgentName','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961e9e772b0','4806684c-e000-3135-6003-1961e9cb6d00','U_ChatId','ChatId','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961ea1dd370','4806684c-e000-3135-6003-1961e9cb6d00','U_Content','Content','InputBox-Text',8000,1),
('4806684c-e000-3135-6003-1961e9dbf6a0','4806684c-e000-3135-6003-1961e9cb6d00','U_RoomId',N'聊天室ID','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961ea08c700','4806684c-e000-3135-6003-1961e9cb6d00','U_SenderId','SenderId','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961ea0e2c70','4806684c-e000-3135-6003-1961e9cb6d00','U_SenderName','SenderName','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961ea14a860','4806684c-e000-3135-6003-1961e9cb6d00','U_SendTime','SendTime','DateBox-DateTime',NULL,1),
('4806684c-e000-3135-6003-1961ea252ec0','4806684c-e000-3135-6003-1961e9cb6d00','U_Type','Type','InputBox-Text',20,1),
('4806684c-e000-3135-6003-1961e9f1fb00','4806684c-e000-3135-6003-1961e9cb6d00','U_UserId','UserId','InputBox-Text',50,1),
('4806684c-e000-3135-6003-1961e9fb6320','4806684c-e000-3135-6003-1961e9cb6d00','U_UserName','UserName','InputBox-Text',50,1);
GO


/* =====================================================
   TsPage
===================================================== */
INSERT INTO TsPage (FId,FName,FTitle,FCode,FUnitId)
VALUES
('4806684c-e000-3135-6003-1961e9cb7a80',N'聊天訊息彙整主列表',N'聊天訊息彙整列表','CUS.ChatMessageSummary.List','4806684c-e000-3135-6003-1961e9cb6d00'),
('4806684c-e000-3135-6003-1961e9cb7b60',N'聊天訊息彙整選擇列表',N'聊天訊息彙整列表','CUS.ChatMessageSummary.SelectList','4806684c-e000-3135-6003-1961e9cb6d00'),
('4806684c-e000-3135-6003-1961e9cb7960',N'聊天訊息彙整表單',N'表單','CUS.ChatMessageSummary.Form','4806684c-e000-3135-6003-1961e9cb6d00');
GO


/* =====================================================
   TsToolItem
===================================================== */
INSERT INTO TsToolItem (FId,FPageId,FCode,FName)
VALUES
('4806684c-e000-3135-6003-1961e9cb7ab0','4806684c-e000-3135-6003-1961e9cb7a80','Add',N'新增'),
('4806684c-e000-3135-6003-1961e9cb7ae0','4806684c-e000-3135-6003-1961e9cb7a80','Open',N'打開'),
('4806684c-e000-3135-6003-1961e9cb7b10','4806684c-e000-3135-6003-1961e9cb7a80','Delete',N'刪除'),
('4806684c-e000-3135-6003-1961e9cb7b20','4806684c-e000-3135-6003-1961e9cb7a80','Refresh',N'重新整理'),
('4806684c-e000-3135-6003-1961e9cb79c0','4806684c-e000-3135-6003-1961e9cb7960','Save',N'保存');
GO


/* =====================================================
   TsMenu
===================================================== */
INSERT INTO TsMenu (FId,FName,FPageId,FEnabled)
VALUES
('4806684c-e000-3135-6003-1961e9cb7bc0',N'聊天訊息彙整','4806684c-e000-3135-6003-1961e9cb7a80',1);
GO