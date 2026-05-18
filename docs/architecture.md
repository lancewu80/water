# 台灣自來水公司 資訊整合系統 — 架構圖

> 使用 [Mermaid](https://mermaid.js.org/) 語法，可直接貼入 GitHub / GitLab / Obsidian / draw.io 等工具渲染。

---

## 1. 系統整體架構 (System Context Diagram)

```mermaid
C4Context
    title 台灣自來水公司 資訊整合系統 — 系統脈絡圖

    Person(user, "內部員工", "使用 ECP 平台的公司員工")
    Person(cusUser, "客服人員", "使用客服聊天系統")

    System_Boundary(water, "台水資訊整合系統") {
        System(ecpSSO, "waterCusSSO", "SSO 單一登入入口\nJSP + ECP 平台")
        System(hrSync, "waterHrSync", "HR 同步 + 聊天摘要\nJava 17 / Maven")
        System(ecpSSOLib, "ecpsso", "SSO 登入紀錄模組\n(ECP Plugin JAR)")
    }

    System_Ext(ecp, "ECP 平台 (Quicksilver)", "Chainsea ECP 8.5\n企業協作平台")
    System_Ext(hrKM, "KM 人事系統", "HR 來源資料庫\n提供 v_KM_USER / v_KM_DEPT")
    System_Ext(ad, "Active Directory", "LDAP 身分驗證")
    System_Ext(chat, "客服聊天系統", "TcChatMessage 等聊天資料表")

    Rel(user, ecpSSO, "登入 / SSO 驗證", "HTTPS / JSON")
    Rel(cusUser, chat, "客服對話", "Web")
    Rel(ecpSSO, ecpSSOLib, "呼叫 SSO 驗證", "Java In-Process")
    Rel(ecpSSO, ad, "LDAP 驗證", "LDAP")
    Rel(ecpSSO, ecp, "Session 建立", "ECP API")
    Rel(hrSync, hrKM, "讀取 HR 資料", "JDBC / SQL")
    Rel(hrSync, ecp, "同步 TsUser / TsDept", "JDBC / ECP DB")
    Rel(hrSync, chat, "讀取聊天記錄", "JDBC")
```

---

## 2. 容器架構圖 (Container Diagram)

```mermaid
graph TB
    subgraph 外部系統
        AD[Active Directory<br/>LDAP]
        KM[(KM 人事系統<br/>v_KM_USER<br/>v_KM_DEPT)]
        CHAT[(客服聊天 DB<br/>TcChatMessage<br/>TrChatSeatStatus)]
    end

    subgraph ECP_Platform[ECP 平台 - JBoss/WildFly]
        direction TB
        subgraph waterCusSSO[waterCusSSO.war - 登入前端]
            LOGIN[login.jsp<br/>帳密登入]
            SSO[sso.jsp<br/>Token 驗證]
            AUTOLOGIN[autologin.jsp]
        end

        subgraph ecpsso_jar[ecpsso.jar - SSO 核心模組]
            SSOSERVICE[SSOLoginLogService<br/>doSSO / doSSOToken]
            SSODAO[SSOLoginLogDao<br/>TsUser 查詢]
            SSOMODEL[SSOLoginLogModel<br/>TpCUSmLoginLog]
        end

        subgraph waterHrSync_jar[waterHrSync.jar - HR 同步 + 聊天摘要]
            direction TB
            subgraph HrSyncModule[HR 同步模組]
                HRTIMER[SyncHrDataRountine<br/>每日 02:00]
                HRSERVICE[HrSyncService<br/>syncHrData]
                HRDAO[HrSyncDao<br/>48 個 DB 方法]
            end
            subgraph ChatModule[聊天摘要模組]
                CHATTIMER[GetChatMessageSummaryRountine<br/>每日執行]
                CHATSERVICE[ChatMessageSummaryService]
                CHATDAO[ChatMessageSummaryDaoImpl]
            end
        end

        ECP_DB[(ECP 主資料庫<br/>TsUser / TsDepartment<br/>TsAccount / TsRole<br/>TpCUSmLoginLog<br/>TpCUSmChatMessageSummary)]
    end

    %% 登入流程
    USER([員工]) -->|POST JSON| LOGIN
    LOGIN -->|LDAP bind| AD
    USER -->|POST token| SSO
    SSO -->|呼叫| SSOSERVICE
    SSOSERVICE --> SSODAO
    SSODAO -->|查詢/寫入| ECP_DB

    %% HR 同步流程
    HRTIMER -->|觸發| HRSERVICE
    HRSERVICE --> HRDAO
    HRDAO -->|讀取| KM
    HRDAO -->|讀寫| ECP_DB

    %% 聊天摘要流程
    CHATTIMER -->|觸發| CHATSERVICE
    CHATSERVICE --> CHATDAO
    CHATDAO -->|讀取| CHAT
    CHATDAO -->|寫入| ECP_DB
```

---

## 3. SSO 登入流程 (Sequence Diagram)

```mermaid
sequenceDiagram
    participant U as 員工瀏覽器
    participant L as login.jsp
    participant S as sso.jsp
    participant SVC as SSOLoginLogService
    participant DAO as SSOLoginLogDao
    participant AD as Active Directory
    participant DB as ECP Database

    Note over U,DB: ① 帳密登入
    U->>L: POST {loginName, password}
    L->>AD: LDAP 驗證
    AD-->>L: 驗證結果
    L->>DB: 建立 ECP Session
    L-->>U: {success: true, token: xxx}

    Note over U,DB: ② SSO Token 驗證 (後續請求)
    U->>S: POST {loginName, token}
    S->>SVC: doSSOToken(loginName, token)
    SVC->>DAO: getSSOToken(token, empId)
    DAO->>DB: 查詢 TpCUSmLoginLog<br/>(5 分鐘內有效)
    DB-->>DAO: token 記錄
    DAO-->>SVC: 是否有效
    alt Token 有效
        SVC-->>S: true
        S-->>U: {success: true}
    else Token 失效
        SVC-->>S: false
        S->>AD: 嘗試 AD fallback 登入
        AD-->>S: 結果
        S-->>U: {success: false}
    end

    Note over U,DB: ③ 寫入稽核紀錄
    SVC->>DAO: addLog(sessionId, token, userName)
    DAO->>DB: INSERT TpCUSmLoginLog
```

---

## 4. HR 同步流程 (Sequence Diagram)

```mermaid
sequenceDiagram
    participant T as Timer (02:00)
    participant SVC as HrSyncService
    participant DAO as HrSyncDao
    participant KM as KM 人事系統
    participant DB as ECP Database

    T->>SVC: syncHrData()

    Note over SVC,KM: Step 1 - 讀取 HR 人員
    SVC->>DAO: getHrUserList()
    DAO->>KM: SELECT v_KM_USER WHERE dept='00*'
    KM-->>DAO: HR 員工清單

    Note over SVC,KM: Step 2 - 同步部門
    SVC->>DAO: getHrDeptList()
    DAO->>KM: SELECT v_KM_DEPT (含父子層級)
    KM-->>DAO: 部門清單
    SVC->>SVC: 拓撲排序 (父部門優先建立)
    loop 每個部門
        SVC->>DAO: upsert TsDepartment
        DAO->>DB: INSERT/UPDATE
    end

    Note over SVC,DB: Step 3-6 - 建立/更新使用者
    SVC->>DAO: getEcpUserList()
    DAO->>DB: SELECT TsUser
    DB-->>DAO: 現有 ECP 使用者

    loop 每個 HR 員工
        alt 使用者已存在
            SVC->>DAO: updateTsUser()
            SVC->>DAO: updateTsAccount()
        else 新使用者
            SVC->>DAO: insertTsUser()
            SVC->>DAO: insertTsAccount()
            SVC->>DAO: ensureAccountIdentity()
        end
    end

    Note over SVC,DB: Step 7 - 指派角色
    SVC->>DAO: getDefaultRoles()
    DAO->>DB: SELECT TsRole
    loop 每個使用者
        SVC->>DAO: assignDefaultRole()
        alt 屬於資訊部門
            SVC->>DAO: assignSysAdminRole()
        end
    end

    SVC-->>T: 同步完成 (新增N/更新M 筆紀錄)
```

---

## 5. 資料庫 ER 圖

```mermaid
erDiagram
    TsUser {
        uuid FId PK
        string FName
        uuid FDepartmentId FK
        bool FEnabled
    }
    TsDepartment {
        uuid FId PK
        string FName
        uuid FParentId FK
        int FTreeLevel
    }
    TsAccount {
        uuid FId PK
        string FLoginName
        string FPassword
        string FEmail
    }
    TsAccountIdentity {
        uuid FId PK
        uuid FAccountId FK
        uuid FEntityId FK
        uuid FIdentityTypeId FK
    }
    TsRole {
        uuid FId PK
        string FName
    }
    TsRoleUser {
        uuid FRoleId FK
        uuid FUserId FK
    }
    TpCUSmLoginLog {
        uuid FId PK
        string U_SessionID
        string U_token
        string FName
        uuid FCreateUserId FK
        string U_CreateUserName
        string U_CreateDepartment
        datetime FCreateTime
    }
    TpCUSmChatMessageSummary {
        uuid FId PK
        string U_AgentId
        string U_AgentName
        string U_ChatId
        string U_Content
        string U_RoomId
        string U_SenderId
        string U_SenderName
        datetime U_SendTime
        string U_Type
        string U_UserId
        string U_UserName
    }

    TsUser }o--|| TsDepartment : "屬於"
    TsAccountIdentity }o--|| TsAccount : "對應帳號"
    TsAccountIdentity }o--|| TsUser : "對應人員"
    TsRoleUser }o--|| TsRole : "角色"
    TsRoleUser }o--|| TsUser : "人員"
    TpCUSmLoginLog }o--|| TsUser : "登入者"
```

---

## 6. 部署架構圖

```mermaid
graph LR
    subgraph 內部網路
        subgraph JBoss_Server[JBoss / WildFly 應用伺服器]
            WAR[waterCusSSO.war<br/>含 ecpsso.jar<br/>含 waterHrSync.jar]
        end
        subgraph DB_Server[資料庫伺服器]
            ECP_DB[(ECP 主資料庫)]
            KM_DB[(KM 人事資料庫)]
            CHAT_DB[(客服聊天資料庫)]
        end
        AD_Server[Active Directory<br/>網域控制站]
    end

    USER([員工 Browser]) -->|HTTPS 443| WAR
    WAR -->|JDBC - executor:default| ECP_DB
    WAR -->|JDBC - executor:km| KM_DB
    WAR -->|JDBC| CHAT_DB
    WAR -->|LDAP 389/636| AD_Server
```
