"""
principles_config.py
--------------------
Single source of truth for all TOGAF software-development principles.

To ADD a new principle
  1. Add an entry to PRINCIPLES (id, name, priority, description, checks_summary)
  2. Add its recommendations to RECOMMENDATIONS
  3. Write a check_pXX() function in checker.py and append it to CHECKERS

To CHANGE metadata or recommendations
  → Edit ONLY this file.  checker.py and report_builder.py read from here.

To CHANGE detection rules (regex patterns)
  → Edit the corresponding check_pXX() function in checker.py

To REMOVE a principle
  1. Delete its entry from PRINCIPLES and RECOMMENDATIONS below
  2. Remove its check_pXX() function from checker.py and remove from CHECKERS
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class PrincipleSpec:
    id: str               # e.g. "P15"
    name: str             # e.g. "Data Security"
    priority: str         # "最高" | "高" | "中" | "低"
    description: str      # One-line summary shown in reports
    checks_summary: str   # Comma-separated list of what the tool checks


# ── Principles registry ────────────────────────────────────────────────────────
# Ordered by priority (highest first), then by TOGAF number.
# This list drives the report order.  Add / remove entries here.

PRINCIPLES: List[PrincipleSpec] = [
    PrincipleSpec(
        id='P15',
        name='Data Security',
        priority='最高',
        description='確保資料在傳輸與儲存過程中受到保護，防止未授權存取與注入攻擊',
        checks_summary='硬編碼密碼/金鑰、SQL 字串拼接、isTokenRequired=false 繞過認證、CORS 萬用字元、加密 API 使用、授權標記存在',
    ),
    PrincipleSpec(
        id='P16',
        name='Technology Independence',
        priority='最高',
        description='透過抽象層與依賴注入隔離具體實作，避免對特定廠商技術產生強依賴',
        checks_summary='直接 new *Impl()、廠商特定 import（mysql/oracle/mssql）、介面比例、依賴注入標記',
    ),
    PrincipleSpec(
        id='P20',
        name='Control Technical Diversity',
        priority='最高',
        description='統一技術棧，避免多種功能相同的函式庫並存造成維護負擔',
        checks_summary='多 JSON 函式庫並存（Jackson/Gson/FastJson）、多日誌框架並存、多 HTTP 用戶端並存',
    ),
    PrincipleSpec(
        id='P21',
        name='Interoperability',
        priority='最高',
        description='採用標準 API 設計與訊息格式，確保系統間可相互溝通',
        checks_summary='硬編碼 IP 位址、JSP 缺 Content-Type 標頭、缺 Swagger/OpenAPI 文件、缺標準序列化工具',
    ),
    PrincipleSpec(
        id='P6',
        name='Service Orientation',
        priority='高',
        description='以服務為導向的模組化設計，降低元件間耦合度',
        checks_summary='缺 Model/DAO/Service/Action 分層、過胖類別（方法數 > 25）',
    ),
    PrincipleSpec(
        id='P5',
        name='Common Use Applications',
        priority='高',
        description='優先使用已有的共用元件，避免在不同模組中重複開發相同功能',
        checks_summary='跨模組重複類別定義、缺 common/util/shared 共用套件',
    ),
    PrincipleSpec(
        id='P4',
        name='Business Continuity',
        priority='高',
        description='系統具備容錯、重試、熔斷能力，確保服務在異常情況下仍能持續運作',
        checks_summary='空 catch 塊、catch(Exception) 未記錄日誌、缺 null 防禦、缺重試機制、缺熔斷器',
    ),
    PrincipleSpec(
        id='P7',
        name='Compliance with Law',
        priority='高',
        description='遵守個資法等相關法規，保護使用者隱私並保留完整稽核軌跡',
        checks_summary='個資/密碼寫入日誌、缺個資脫敏處理、缺稽核日誌',
    ),
]

# Quick-lookup dict: id → PrincipleSpec
PRINCIPLES_BY_ID: dict[str, PrincipleSpec] = {p.id: p for p in PRINCIPLES}


# ── Improvement recommendations ────────────────────────────────────────────────
# Update the list for a principle without touching checker.py or report_builder.py.

RECOMMENDATIONS: dict[str, List[str]] = {
    'P15': [
        '使用設定檔（application.properties / Vault）管理密碼，禁止硬編碼',
        '採用 PreparedStatement 或 MyBatis #{} 參數化查詢防止 SQL 注入',
        '所有 API 端點加入 @PreAuthorize 或 Spring Security 過濾器',
        '傳輸層使用 TLS 1.2+，敏感欄位儲存前加密（AES-256）',
        '跨域限制明確來源列表，禁止 Access-Control-Allow-Origin: *',
    ],
    'P16': [
        '透過介面定義服務合約，實作類別以 Spring @Service 注入',
        '避免直接 new *Impl()，改用建構子注入或工廠方法',
        '資料庫驅動使用 JDBC 抽象層（Spring JdbcTemplate / JPA）',
        '第三方服務呼叫封裝至 Adapter 類別，隔離廠商 SDK 依賴',
    ],
    'P20': [
        '統一 JSON 序列化框架（建議 Jackson，在 pom.xml 排除其他庫）',
        '統一日誌框架為 SLF4J + Logback，移除 log4j 直接依賴',
        '制定技術選型清單並透過 Maven Enforcer Plugin 強制執行',
        '定期執行 mvn dependency:analyze 檢查未使用/衝突依賴',
    ],
    'P21': [
        '設定檔集中管理服務 URL，禁止硬編碼 IP 位址',
        'JSP 回應 JSON 時明確設定 response.setContentType("application/json;charset=UTF-8")',
        '使用 Swagger/OpenAPI 標記 (@Api, @ApiOperation) 文件化所有端點',
        '遵循 RESTful 設計：GET/POST/PUT/DELETE 語意化，回應格式統一',
    ],
    'P6': [
        '嚴格分層：Controller → Service Interface → ServiceImpl → DAO Interface → DAOImpl',
        '方法數超過 20 個的類別應拆分（單一責任原則）',
        '共用業務邏輯抽取至 Service 層，禁止在 JSP/Action 中直接操作資料庫',
        '模組間透過定義好的 Service 介面通訊，避免直接引用其他模組的 Impl 類別',
    ],
    'P5': [
        '重複類別整合至公共模組（如 common-utils JAR）',
        '建立 Maven Parent POM 集中管理版本依賴',
        '確立禁止複製程式碼的開發規範，改用共享函式庫',
        '定期 Code Review 識別跨模組重複邏輯',
    ],
    'P4': [
        '所有 catch 塊必須記錄日誌（log.error(e.getMessage(), e)），禁止空 catch',
        '遠端呼叫加入 @Retryable 或自行實作重試（最多 3 次，指數退避）',
        '整合 Resilience4j CircuitBreaker 防止雪崩效應',
        '所有外部輸入參數執行 null 檢查並回傳有意義的錯誤訊息',
        '使用 Optional<T> 替代返回 null 的方法',
    ],
    'P7': [
        '日誌中禁止輸出密碼、身分證號、信用卡號等個資',
        '個資欄位顯示前進行脫敏（手機：09xx-xxx-xxx，身分證：A12x-xxxx）',
        '重要操作（登入/修改/刪除）寫入稽核日誌並記錄操作人員與時間',
        '依個資法要求提供資料查閱、更正、刪除機制',
        '定期稽核日誌備份留存 2 年以上',
    ],
}


def get_recommendations(principle_id: str) -> List[str]:
    return RECOMMENDATIONS.get(principle_id, ['請參閱 TOGAF 相關準則文件'])


def get_spec(principle_id: str) -> PrincipleSpec | None:
    return PRINCIPLES_BY_ID.get(principle_id)
