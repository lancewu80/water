# 台灣自來水公司 資訊整合系統 — 詳細設計文件

**版本**: 1.0  
**日期**: 2026-05-14  
**作者**: Lance Wu  
**狀態**: UAT v2

---

## 目錄

1. [專案概述](#1-專案概述)
2. [技術堆疊](#2-技術堆疊)
3. [模組說明](#3-模組說明)
   - 3.1 [ecpsso — SSO 登入紀錄核心模組](#31-ecpsso--sso-登入紀錄核心模組)
   - 3.2 [waterCusSSO — 前端登入入口](#32-watercussso--前端登入入口)
   - 3.3 [waterHrSync — HR 同步與聊天摘要](#33-waterHrSync--hr-同步與聊天摘要)
4. [資料庫設計](#4-資料庫設計)
5. [API 規格](#5-api-規格)
6. [排程設計](#6-排程設計)
7. [安全設計](#7-安全設計)
8. [錯誤處理與日誌](#8-錯誤處理與日誌)
9. [部署與設定](#9-部署與設定)
10. [已知限制與待辦事項](#10-已知限制與待辦事項)

---

## 1. 專案概述

### 1.1 背景

台灣自來水公司（台水）委託開發一套資訊整合系統，將人事系統（KM）、企業協作平台（ECP）、客服聊天系統三個核心系統整合，達成：

- **單一登入（SSO）**：員工只需一組帳號即可存取 ECP 平台，透過 Token 機制串接外部系統。
- **HR 資料同步**：每日自動將 KM 人事系統的員工與部門資料同步至 ECP，保持帳號資料一致性。
- **聊天摘要彙整**：每日彙整客服聊天記錄，儲存至 ECP 資料庫供後續分析。

### 1.2 系統邊界

| 系統 | 角色 | 擁有方 |
|------|------|--------|
| ECP (Quicksilver) | 主要企業協作平台，本系統的部署容器 | Chainsea 鏈鎖科技 |
| KM 人事系統 | HR 資料來源 (唯讀) | 台水 IT |
| Active Directory | 身分驗證 (LDAP) | 台水 IT |
| 客服聊天系統 | 聊天資料來源 (唯讀) | 台水 IT |
| **本系統** | 整合中介層 | Ai3 / 台水 |

### 1.3 主要使用者

| 角色 | 使用方式 |
|------|----------|
| 內部員工 | 透過 SSO 登入 ECP 平台 |
| IT 部門 | 自動同步帳號，系統管理員角色自動指派 |
| 客服人員 | 聊天記錄自動彙整，無需手動操作 |

---

## 2. 技術堆疊

| 層級 | 技術 | 版本 |
|------|------|------|
| 語言 | Java | 17 |
| 建置工具 | Maven | 3.x |
| 應用框架 | Quicksilver + ECP | 7.1.31.beta22 + 8.5.02.36 |
| 應用伺服器 | JBoss / WildFly | (依 ECP 平台版本) |
| 前端 | JSP (Jakarta EE) | 4.0 |
| Servlet | Jakarta Servlet | 4.0 |
| JSON 處理 | org.json | 20240303 |
| 日誌 | SLF4J + Log4j2 | 2.0.16 |
| 資料庫 | MariaDB / SQL Server | (依部署環境) |
| 身分驗證 | LDAP / Active Directory | — |
| 部署單元 | WAR + JAR (plugin) | — |

---

## 3. 模組說明

### 3.1 ecpsso — SSO 登入紀錄核心模組

#### 概述

以 ECP Plugin JAR 形式部署，封裝 SSO Token 驗證與登入稽核邏輯。由 `waterCusSSO` 的 JSP 頁面在執行期呼叫。

#### 包結構

```
com.chainsea.water.ecpsso/
├─ SSOLoginLogHome.java          # Service Locator，載入設定、取得服務實體
├─ model/
│   └─ SSOLoginLogModel.java     # EntityModel 擴展，對應 TpCUSmLoginLog
├─ dao/
│   ├─ SSOLoginLogDao.java       # DAO 介面
│   └─ impl/SSOLoginLogDaoImpl.java
├─ service/
│   ├─ SSOLoginLogService.java   # Service 介面
│   └─ impl/SSOLoginLogServiceImpl.java
├─ api/
│   └─ impl/SSOLoginLogApiImpl.java  # (目前停用)
└─ action/
    └─ impl/SSOLoginLogActionImpl.java  # (目前停用)
```

#### 關鍵設計決策

**Token 有效期 5 分鐘**：`getSSOToken()` 查詢條件限制在最近 5 分鐘內建立的 Token，防止 Token 被重複使用或長期有效帶來的安全風險。

```java
// SSOLoginLogDaoImpl.getSSOToken()
// WHERE FCreateTime >= NOW() - INTERVAL 5 MINUTE
//   AND U_token = :token AND FCreateUserId = :empId
```

**Unit ID 隔離**：ECP 平台以 Unit ID 區隔不同外掛的資料 Cache Region，`ecpsso` 使用 `df6c8bac-d9ce-4e6c-c404-18fc8f33cec0`，Cache Region 為 `cus_ssologinlog`。

#### 服務方法

| 方法 | 說明 | 輸入 | 輸出 |
|------|------|------|------|
| `doSSO(loginName)` | 驗證帳號是否存在於 ECP，並記錄登入 | loginName | boolean |
| `doSSOToken(loginName, token)` | 驗證 5 分鐘內的有效 Token | loginName, token | boolean |
| `checkUser(loginName)` | 查詢 TsUser/TsAccount 確認帳號存在 | loginName | UserInfo |
| `addLog(sessionId, token, ...)` | 寫入登入稽核記錄 | session 資訊 | void |

---

### 3.2 waterCusSSO — 前端登入入口

#### 概述

以 WAR 形式部署於 ECP 平台，包含登入頁面（JSP）與 `ecpsso.jar` 等依賴 JAR。負責接收使用者請求、呼叫 AD 驗證、轉送 SSO Token 驗證。

#### 檔案結構

```
waterCusSSO/
└─ sso/ecp/
    ├─ WEB-INF/
    │   ├─ web.xml
    │   ├─ jboss-deployment-structure.xml
    │   └─ lib/                     # 含 ecpsso.jar, waterHrSync.jar 等
    └─ custom/login/
        ├─ login.jsp                # 主要帳密登入端點
        ├─ sso.jsp                  # Token 驗證端點
        ├─ autologin.jsp            # 自動登入輔助
        ├─ login.html               # 靜態登入頁
        ├─ login_cookie.html        # Cookie 登入頁
        ├─ login_ldap.html          # LDAP 登入頁
        └─ update/                  # sso.jsp 版本歸檔
```

#### login.jsp 設計

**HTTP 方法**: POST  
**Content-Type**: application/json  
**CORS**: 支援跨域（設有 CORS Header）

**請求格式**:
```json
{
  "loginName": "empId or username",
  "password": "plaintext password"
}
```

**回應格式**:
```json
{
  "success": true
}
```

**處理流程**:
1. 解析 JSON 請求體
2. 呼叫 Quicksilver API 進行 AD/LDAP 驗證
3. 驗證成功後設定語言 Cookie
4. 建立 ECP Session
5. 記錄請求時間戳、來源 IP、使用者名稱至伺服器日誌

#### sso.jsp 設計

**HTTP 方法**: POST  
**Content-Type**: application/json  

**請求格式**:
```json
{
  "loginName": "empId",
  "token": "UUID or custom token"
}
```

**回應格式**:
```json
{
  "success": true
}
```

**處理流程**:
1. 解析 JSON 請求體
2. 呼叫 `SSOLoginLogHome.getService().doSSOToken(loginName, token)`
3. 若 Token 有效 → 回傳成功
4. 若 Token 失效 → 嘗試 AD Fallback 登入
5. 寫入日誌至 `sso_auth.log`

---

### 3.3 waterHrSync — HR 同步與聊天摘要

#### 概述

以 ECP Plugin JAR 形式部署，包含兩個子模組：

- **hrsync**: 每日凌晨 02:00 將 KM 人事資料同步至 ECP
- **chatmessagesummary**: 每日彙整前一日聊天記錄

#### 包結構

```
com.chainsea.water/
├─ hrsync/
│   ├─ HrSyncHome.java
│   ├─ model/HrSyncModel.java
│   ├─ dao/
│   │   ├─ HrSyncDao.java           # 48 個 DB 操作方法
│   │   └─ impl/HrSyncDaoImpl.java
│   ├─ service/
│   │   ├─ HrSyncService.java
│   │   └─ impl/HrSyncServiceImpl.java
│   └─ timer/SyncHrDataRountine.java
│
└─ chatmessagesummary/
    ├─ ChatMessageSummaryHome.java
    ├─ model/ChatMessageSummaryModel.java
    ├─ dao/
    │   ├─ ChatMessageSummaryDao.java
    │   └─ impl/ChatMessageSummaryDaoImpl.java
    ├─ service/
    │   ├─ ChatMessageSummaryService.java
    │   └─ impl/ChatMessageSummaryServiceImpl.java
    ├─ api/impl/ChatMessageSummaryApiImpl.java
    ├─ action/impl/ChatMessageSummaryActionImpl.java
    └─ timer/GetChatMessageSummaryRountine.java
```

#### 3.3.1 HR 同步模組詳細設計

**Unit ID**: `4806684c-e000-3135-6003-1961e9cb6d01`

**資料來源**:

| 來源 | 說明 | Executor |
|------|------|----------|
| `v_KM_USER` | HR 員工 View（部門 ID 以 `00` 開頭） | `km` |
| `v_KM_DEPT` | HR 部門 View（含父子關係） | `km` |

**v_KM_USER 欄位對應**:

| KM 欄位 | ECP 欄位 | 說明 |
|---------|----------|------|
| EMPLOYEEID | TsUser.FId (衍生) | 員工編號 |
| DISPLAYNAME | TsUser.FName | 顯示名稱 |
| EMAILADDRESS | TsAccount.FEmail | 電子郵件 |
| LOGINID | TsAccount.FLoginName | 登入帳號 |
| DEPARTMENTID | TsUser.FDepartmentId | 所屬部門 |

**syncHrData() 執行步驟**:

```
Step 1: 從 v_KM_USER 讀取 HR 員工清單（dept starts with '00'）
Step 2: 從 v_KM_DEPT 讀取部門清單，進行拓撲排序後同步至 TsDepartment
Step 3: 建立 HR 員工 LoginId → HrUser 的 Map
Step 4: 讀取現有 ECP TsUser 清單
Step 5: 讀取 IT 部門 ID 清單（部門名稱含「資訊」）
Step 6: 讀取預設角色與 SysAdmin 角色
Step 7: 逐一比對，新增或更新 TsUser / TsAccount
Step 8: 確保 TsAccountIdentity 存在（帳號-人員對應）
Step 9: 指派預設角色；IT 部門額外指派 SysAdmin 角色
Step 10: 記錄同步結果（新增 N 筆 / 更新 M 筆）
```

**部門拓撲排序**：父部門必須先於子部門寫入 ECP，否則外鍵約束失敗。`syncDepartments()` 以廣度優先（BFS / 拓撲排序）處理 `v_KM_DEPT.BELONGTO` 父子關係。

**角色指派規則**:

| 條件 | 角色 |
|------|------|
| 所有同步員工 | 預設角色（hrsync.properties 中設定） |
| 部門名稱含「資訊」 | 額外指派 SysAdmin 角色 |

**HrSyncHome 設定參數**:

| 屬性 | 說明 | 來源 |
|------|------|------|
| `accountIdentityTypeId` | TsAccountIdentity 使用的身分類型 UUID | `hrsync.properties` |
| `accountDefaultPassword` | 新帳號的預設密碼（加密儲存） | `hrsync.properties` |
| `TsDepartmentRootFId` | ECP 部門樹根節點 UUID | `hrsync.properties` |

#### 3.3.2 聊天摘要模組詳細設計

**Unit ID**: `4806684c-e000-3135-6003-1961e9cb6d00`

**資料來源查詢**（跨表 JOIN）:

```sql
SELECT
    TcChatMessage.*,
    TrChatSeatStatus.AgentId, TrChatSeatStatus.AgentName,
    TsUser.FName AS UserName,
    TcContact.ContactId,
    TcChatMan.*
FROM TcChatMessage
JOIN TrChatSeatStatus ON ...
JOIN TsUser ON ...
JOIN TcContact ON ...
JOIN TcChatMan ON ...
WHERE TCSS.FCreateTime = :targetDate
```

**彙整流程**:
1. `GetChatMessageSummaryRountine` 觸發（每日執行）
2. 取得目標日期（預設昨日）
3. `ChatMessageSummaryService.getChatMessageSummary(targetDate)` 呼叫 DAO
4. Batch INSERT 寫入 `TpCUSmChatMessageSummary`

**目標日期解析**：
- 若 Timer 帶有 args 且格式為 `yyyy-MM-dd` → 使用指定日期
- 否則 → 使用 `LocalDate.now().minusDays(1)`

---

## 4. 資料庫設計

### 4.1 資料庫連線設定

| Executor 名稱 | 用途 | 資料庫 |
|---------------|------|--------|
| `default` | ECP 主資料庫（讀寫） | ECP DB |
| `km` | KM 人事系統（唯讀） | KM DB |
| (預設) | 客服聊天資料庫（唯讀） | Chat DB |

### 4.2 自訂資料表

#### TpCUSmLoginLog — SSO 登入稽核

| 欄位 | 型別 | 說明 |
|------|------|------|
| FId | UUID PK | 主鍵 |
| U_SessionID | VARCHAR | ECP Session ID |
| U_token | VARCHAR | SSO Token |
| FName | VARCHAR | 登入狀態（LoginStatus） |
| FCreateUserId | UUID FK | 登入使用者 ID (TsUser) |
| FCreateDepartmentId | UUID FK | 所屬部門 ID (TsDepartment) |
| U_CreateUserName | VARCHAR | 登入使用者名稱（冗餘備份） |
| U_CreateDepartment | VARCHAR | 部門名稱（冗餘備份） |
| FCreateTime | DATETIME | 建立時間（查詢效能關鍵欄位） |

> `FCreateTime` 需建立索引，`getSSOToken()` 的 5 分鐘範圍查詢依賴此欄位效能。

#### TpCUSmChatMessageSummary — 聊天摘要

| 欄位 | 型別 | 說明 |
|------|------|------|
| FId | UUID PK | 主鍵 |
| U_AgentId | VARCHAR | 客服坐席 ID |
| U_AgentName | VARCHAR | 客服坐席姓名 |
| U_ChatId | VARCHAR | 聊天室 ID |
| U_Content | TEXT | 訊息內容 |
| U_RoomId | VARCHAR | 聊天房間 ID |
| U_SenderId | VARCHAR | 發送者 ID |
| U_SenderName | VARCHAR | 發送者姓名 |
| U_SendTime | DATETIME | 發送時間 |
| U_Type | VARCHAR | 訊息類型 |
| U_UserId | VARCHAR | 客戶使用者 ID |
| U_UserName | VARCHAR | 客戶使用者姓名 |

### 4.3 ECP 平台核心資料表（唯讀參考）

| 資料表 | 說明 |
|--------|------|
| TsUser | ECP 使用者主表 |
| TsDepartment | 部門樹狀結構 |
| TsAccount | 登入帳號 |
| TsAccountIdentity | 帳號 ↔ 人員對應（支援多身分） |
| TsRole | 角色定義 |
| TsRoleUser | 角色指派關係 |

---

## 5. API 規格

### 5.1 Active Endpoints（JSP）

#### POST /sso/ecp/custom/login/login.jsp

帳密登入。

**Request Headers**:
```
Content-Type: application/json
Origin: (任意，支援 CORS)
```

**Request Body**:
```json
{
  "loginName": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "success": true
}
```

**Error Response**:
```json
{
  "success": false,
  "message": "帳號或密碼錯誤"
}
```

---

#### POST /sso/ecp/custom/login/sso.jsp

SSO Token 驗證。

**Request Body**:
```json
{
  "loginName": "string",
  "token": "string"
}
```

**Response**:
```json
{
  "success": true
}
```

**驗證邏輯**:
1. 查詢 `TpCUSmLoginLog` — 5 分鐘內是否有對應 token
2. 若無效 → AD fallback 嘗試
3. 寫入 `sso_auth.log`

---

### 5.2 Disabled Endpoints（API 框架，暫未啟用）

| Path | 方法 | 說明 |
|------|------|------|
| `/TCBEcpSSO/EcpSSO` | POST | doSSO() ECP API 版本 |
| `/TCBEcpSSO/SSOToken` | POST | doSSOToken() ECP API 版本 |

> 這些 Endpoint 使用 `@Api` 標註，標記 `isTokenRequired = false`，目前程式碼已存在但被停用（方法內容為空或已移至 JSP 處理）。

---

## 6. 排程設計

| 排程名稱 | Class | 執行時間 | 說明 |
|----------|-------|----------|------|
| HR 同步 | `SyncHrDataRountine` | 每日 **02:00** | 同步人員/部門至 ECP |
| 聊天摘要 | `GetChatMessageSummaryRountine` | 每日（預設昨日） | 彙整前一日聊天記錄 |

**排程約束**:
- HR 同步排定在 04:00 備份作業之前執行，確保備份時資料已是最新狀態。
- 兩個排程不應同時執行，避免資料庫鎖衝突。

**Timer Routine 介面**（ECP 平台提供）:

```java
public interface TimerRoutine {
    void execute(String[] args);
}
```

Timer args 可在 ECP 後台設定，`GetChatMessageSummaryRountine` 支援傳入指定日期參數。

---

## 7. 安全設計

### 7.1 Token 安全

| 機制 | 說明 |
|------|------|
| 有效期限 | Token 5 分鐘後自動失效 |
| 綁定使用者 | Token 與 `empId` 綁定，無法跨使用者使用 |
| Fallback | Token 失效時嘗試 AD 重新驗證，而非直接放行 |
| 稽核日誌 | 所有驗證嘗試（成功/失敗）均寫入 `TpCUSmLoginLog` 與 `sso_auth.log` |

### 7.2 密碼安全

| 項目 | 說明 |
|------|------|
| 預設密碼 | 儲存於 `hrsync.properties`，以加密格式儲存（ECP 平台加密機制） |
| AD 驗證 | 密碼不落地，由 LDAP bind 操作完成驗證 |
| LDAP 連線 | 建議使用 LDAPS（636 port）加密傳輸 |

### 7.3 CORS

`login.jsp` 設有 CORS Header 允許跨域請求，應確認 `Access-Control-Allow-Origin` 的白名單設定（目前版本確認是否為 `*` 或限定網域）。

### 7.4 資料隔離

- KM 人事資料庫使用獨立 Executor（`km`），僅有讀取權限，無法從 ECP 模組寫入 KM 資料庫。
- 聊天資料庫同樣為唯讀存取。

---

## 8. 錯誤處理與日誌

### 8.1 日誌策略

| 日誌 | 位置 | 內容 |
|------|------|------|
| `sso_auth.log` | 應用伺服器日誌目錄 | SSO Token 驗證結果、來源 IP、時間戳 |
| SLF4J / Log4j2 | ECP 標準日誌 | HR 同步執行結果（新增 N 筆、更新 M 筆）|
| JSP 標準輸出 | 伺服器 stdout | 登入請求的時間戳、IP、使用者名稱 |

### 8.2 HR 同步錯誤處理

| 情境 | 處理方式 |
|------|----------|
| KM DB 連線失敗 | 拋出例外，本次同步中止，記錄 ERROR log |
| 部門父節點不存在 | 拓撲排序保證父節點先建立，若仍失敗則跳過該部門並記錄警告 |
| 使用者資料衝突 | 以 `loginName` 為唯一鍵，EXISTS 判斷後做 INSERT 或 UPDATE |
| 角色指派失敗 | 記錄警告，不中止整體同步流程 |

### 8.3 聊天摘要錯誤處理

| 情境 | 處理方式 |
|------|----------|
| 無聊天記錄 | 返回空集合，不執行 INSERT，記錄 INFO log |
| 資料重複插入 | 以 FId UUID 為主鍵，重跑時若 FId 重複會拋 PK 違反例外 |

> **待改善**：聊天摘要模組目前缺乏冪等設計，若 Timer 重複執行可能造成重複資料。建議加入執行前先刪除當日資料的機制（DELETE + INSERT）或改用 UPSERT。

---

## 9. 部署與設定

### 9.1 部署步驟

```
1. 編譯 ecpsso      → 產生 ecpsso.jar
2. 編譯 waterHrSync → 產生 waterHrSync.jar
3. 將 JAR 複製至 waterCusSSO/WEB-INF/lib/
4. 打包 waterCusSSO → 產生 waterCusSSO.war
5. 部署 WAR 至 JBoss/WildFly
6. 在 ECP 後台設定 Timer Routine（HR sync 02:00、Chat summary 每日）
```

### 9.2 hrsync.properties 設定

```properties
# TsAccountIdentity 使用的身分類型 UUID（請勿任意修改）
accountIdentityTypeId=564cf69e-76d6-4baf-b584-6e04c2911dae

# 新建帳號的預設密碼（ECP 加密格式）
accountDefaultPassword=<encrypted>

# ECP 部門樹根節點 UUID
TsDepartmentRootFId=00000000-0000-0000-1001-000000000001
```

### 9.3 資料庫 Executor 設定（ECP 後台）

| Executor | 對應資料庫 | 備註 |
|----------|-----------|------|
| `default` | ECP 主資料庫 | 讀寫 |
| `km` | KM 人事資料庫 | 唯讀 |

### 9.4 環境需求

| 項目 | 需求 |
|------|------|
| Java | 17+ |
| JBoss/WildFly | ECP 8.5 相容版本 |
| ECP | 8.5.02.36 |
| Quicksilver | 7.1.31.beta22 |
| 網路 | 應用伺服器可連線至 AD、KM DB、Chat DB |

---

## 10. 已知限制與待辦事項

### 10.1 已知限制

| 項目 | 說明 |
|------|------|
| API 端點停用 | `SSOLoginLogApi` 的 ECP API 端點目前為空實作，功能由 JSP 承擔 |
| 無 Token Revoke 機制 | Token 無法主動撤銷，只能等待 5 分鐘自然過期 |
| 聊天摘要非冪等 | 重複執行會產生重複資料 |
| CORS 白名單 | `login.jsp` 的 CORS 設定需確認是否鎖定特定來源域名 |
| 帳號停用邏輯 | KM 人員離職後，ECP 帳號的停用/刪除流程未在程式碼中看到，可能需要手動處理 |

### 10.2 建議改善項目

| 優先級 | 項目 | 說明 |
|--------|------|------|
| 高 | 聊天摘要冪等設計 | 執行前先 DELETE 當日資料，或改用 UPSERT |
| 高 | 帳號離職停用 | 增加「HR 中不存在的 ECP 帳號自動停用」邏輯 |
| 中 | Token 延長機制 | 提供 refresh token 或延長有效期至 30 分鐘 |
| 中 | CORS 白名單 | 限制 `Access-Control-Allow-Origin` 為特定域名 |
| 低 | API 端點啟用 | 啟用 ECP API 版本的 SSO 端點，取代 JSP 直接處理 |
| 低 | 單元測試 | 目前無測試程式碼，建議補充 HrSyncService、SSOLoginLogService 的單元測試 |

---

*本文件依據原始碼分析自動產生，如有疑義請以原始碼為準。*
