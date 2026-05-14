const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  TableOfContents, UnderlineType
} = require('docx');
const fs = require('fs');

// ── colour palette ──────────────────────────────────────────────────────────
const BLUE_DARK  = "1F4E79";  // cover title
const BLUE_MID   = "2E75B6";  // h1 accent bar
const BLUE_LIGHT = "D5E8F0";  // table header fill
const BLUE_PALE  = "EBF3FB";  // alt table row
const GRAY_LINE  = "BFBFBF";  // divider
const CODE_BG    = "F2F2F2";  // code block

// ── page geometry (A4, margins 2.5 cm ≈ 1417 DXA) ───────────────────────
const PAGE_W  = 11906;
const PAGE_H  = 16838;
const MARGIN  = 1440;  // 1 inch ≈ 2.54 cm
const CONTENT = PAGE_W - MARGIN * 2;  // 9026 DXA

// ── helpers ─────────────────────────────────────────────────────────────────
const border = (color = GRAY_LINE) => ({ style: BorderStyle.SINGLE, size: 1, color });
const cellBorders = (color = GRAY_LINE) => ({
  top: border(color), bottom: border(color),
  left: border(color), right: border(color)
});
const cellPad = { top: 100, bottom: 100, left: 160, right: 160 };

function hdrCell(text, widthDxa) {
  return new TableCell({
    borders: cellBorders(BLUE_MID),
    width: { size: widthDxa, type: WidthType.DXA },
    shading: { fill: BLUE_LIGHT, type: ShadingType.CLEAR },
    margins: cellPad,
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, size: 20, font: "微軟正黑體", color: BLUE_DARK })]
    })]
  });
}

function dataCell(text, widthDxa, altRow = false) {
  return new TableCell({
    borders: cellBorders(),
    width: { size: widthDxa, type: WidthType.DXA },
    shading: altRow ? { fill: BLUE_PALE, type: ShadingType.CLEAR } : undefined,
    margins: cellPad,
    children: [new Paragraph({
      children: [new TextRun({ text, size: 19, font: "微軟正黑體" })]
    })]
  });
}

function dataRow(cells, altRow = false) {
  return new TableRow({
    children: cells.map(([text, w]) => dataCell(text, w, altRow))
  });
}

function makeTable(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => hdrCell(h, colWidths[i]))
      }),
      ...rows.map((row, ri) =>
        new TableRow({
          children: row.map((text, ci) => dataCell(text, colWidths[ci], ri % 2 === 1))
        })
      )
    ]
  });
}

function sp(before = 0, after = 0) {
  return { spacing: { before, after } };
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, font: "微軟正黑體", bold: true, size: 32, color: BLUE_DARK })],
    spacing: { before: 480, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: BLUE_MID, space: 4 } }
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, font: "微軟正黑體", bold: true, size: 26, color: BLUE_MID })],
    spacing: { before: 320, after: 120 }
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, font: "微軟正黑體", bold: true, size: 22 })],
    spacing: { before: 240, after: 80 }
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, size: 20, font: "微軟正黑體", ...opts })],
    spacing: { before: 60, after: 60 }
  });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    children: [new TextRun({ text, size: 20, font: "微軟正黑體" })],
    spacing: { before: 40, after: 40 }
  });
}

function code(text) {
  return new Paragraph({
    children: [new TextRun({ text, size: 18, font: "Courier New" })],
    shading: { fill: CODE_BG, type: ShadingType.CLEAR },
    spacing: { before: 20, after: 20 },
    indent: { left: 360 }
  });
}

function note(text) {
  return new Paragraph({
    children: [
      new TextRun({ text: "⚠ 注意：", bold: true, size: 19, font: "微軟正黑體", color: "C55A11" }),
      new TextRun({ text, size: 19, font: "微軟正黑體", color: "C55A11" })
    ],
    spacing: { before: 80, after: 80 },
    indent: { left: 360 }
  });
}

function pb() { return new Paragraph({ children: [new PageBreak()] }); }

function labeledPara(label, value) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [
      new TextRun({ text: label + "：", bold: true, size: 20, font: "微軟正黑體" }),
      new TextRun({ text: value, size: 20, font: "微軟正黑體" })
    ]
  });
}

// ── ASCII diagrams ───────────────────────────────────────────────────────────
const systemContextDiagram = [
  "┌────────────────────────────────────────────────────────────────────────┐",
  "│                    台灣自來水公司 資訊整合系統                              │",
  "├────────────────────────────────────────────────────────────────────────┤",
  "│  使用者                   台水整合系統邊界                  外部系統         │",
  "│                                                                        │",
  "│  ┌────────┐  HTTPS/JSON  ┌─────────────────┐  LDAP   ┌────────────┐  │",
  "│  │ 內部員工 │ ──────────▶ │  waterCusSSO     │ ──────▶ │   Active   │  │",
  "│  └────────┘             │  (JSP 登入前端)   │         │ Directory  │  │",
  "│                         └────────┬────────┘         └────────────┘  │",
  "│  ┌────────┐              In-Proc │                                    │",
  "│  │ 客服人員 │             ┌───────▼─────────┐  JDBC   ┌────────────┐  │",
  "│  └──┬─────┘             │    ecpsso.jar    │ ──────▶ │  ECP 主DB  │  │",
  "│     │                   │  (SSO 核心模組)  │         └────────────┘  │",
  "│     │ Web               └─────────────────┘                          │",
  "│     ▼                                                                  │",
  "│  ┌──────────┐  JDBC     ┌─────────────────┐  JDBC   ┌────────────┐  │",
  "│  │客服聊天系統│ ◀──────── │  waterHrSync     │ ──────▶ │  KM 人事DB │  │",
  "│  └──────────┘           │  (HR 同步模組)   │         └────────────┘  │",
  "│                         └─────────────────┘                          │",
  "└────────────────────────────────────────────────────────────────────────┘",
];

const containerDiagram = [
  "┌─────────────────────── JBoss / WildFly 應用伺服器 ─────────────────────┐",
  "│                                                                        │",
  "│  ┌─────────── waterCusSSO.war ────────────────────────────────────┐   │",
  "│  │  login.jsp   sso.jsp   autologin.jsp                           │   │",
  "│  │  ↕ CORS/JSON  ↕ Token驗證                                      │   │",
  "│  └──────────────────────┬─────────────────────────────────────────┘   │",
  "│                         │ Java In-Process Call                         │",
  "│  ┌─────────── ecpsso.jar (Plugin) ───────────────────────────────┐    │",
  "│  │  SSOLoginLogService → SSOLoginLogDao → TpCUSmLoginLog         │    │",
  "│  └───────────────────────────────────────────────────────────────┘    │",
  "│                                                                        │",
  "│  ┌─────────── waterHrSync.jar (Plugin) ──────────────────────────┐    │",
  "│  │  ┌─ HR同步子模組 ──────────────────┐                          │    │",
  "│  │  │  SyncHrDataRountine (02:00)     │                          │    │",
  "│  │  │  HrSyncService → HrSyncDao      │                          │    │",
  "│  │  └─────────────────────────────────┘                          │    │",
  "│  │  ┌─ 聊天摘要子模組 ────────────────┐                          │    │",
  "│  │  │  GetChatMessageSummaryRountine  │                          │    │",
  "│  │  │  ChatMessageSummaryService      │                          │    │",
  "│  │  └─────────────────────────────────┘                          │    │",
  "│  └───────────────────────────────────────────────────────────────┘    │",
  "│                                                                        │",
  "└──────────────────────────────────┬─────────────────────────────────────┘",
  "                                   │",
  "        ┌──────────────────────────┼──────────────────────────┐",
  "        ▼                          ▼                          ▼",
  "  ┌──────────┐             ┌──────────────┐           ┌────────────┐",
  "  │ ECP 主DB │             │  KM 人事DB   │           │ 客服聊天DB │",
  "  │(讀寫)    │             │  (唯讀)       │           │  (唯讀)    │",
  "  └──────────┘             └──────────────┘           └────────────┘",
];

const ssoFlowDiagram = [
  "員工瀏覽器     login.jsp    Active Directory    ECP Database",
  "    │               │               │                │",
  "    │ POST {loginName,password}      │                │",
  "    │──────────────▶│               │                │",
  "    │               │ LDAP bind     │                │",
  "    │               │──────────────▶│                │",
  "    │               │◀──────────────│                │",
  "    │               │  建立 Session  │                │",
  "    │               │────────────────────────────────▶",
  "    │ {success:true,token}           │                │",
  "    │◀──────────────│               │                │",
  "    │               │               │                │",
  "    │ (後續請求)     │               │                │",
  "    │  sso.jsp                       │                │",
  "    │──────────────────────────────▶│                │",
  "    │               │ doSSOToken()  │                │",
  "    │               │──────────────────────▶          │",
  "    │               │ getSSOToken() │    查詢 TpCUSmLoginLog (5分鐘)",
  "    │               │               │────────────────▶│",
  "    │               │               │◀────────────────│",
  "    │               │               │                │",
  "    │ Token有效 → {success:true}     │                │",
  "    │ Token失效 → AD fallback → {success:false}        │",
  "    │◀──────────────│               │                │",
  "    │               │   INSERT TpCUSmLoginLog         │",
  "    │               │────────────────────────────────▶",
];

const hrSyncFlowDiagram = [
  "Timer(02:00)   HrSyncService   HrSyncDao   KM人事系統   ECP Database",
  "     │               │              │            │              │",
  "     │ syncHrData()  │              │            │              │",
  "     │──────────────▶│              │            │              │",
  "     │               │ getHrUserList()           │              │",
  "     │               │─────────────▶│            │              │",
  "     │               │              │ SELECT v_KM_USER          │",
  "     │               │              │───────────▶│              │",
  "     │               │              │◀───────────│              │",
  "     │               │◀─────────────│            │              │",
  "     │               │ getHrDeptList()           │              │",
  "     │               │─────────────▶│ SELECT v_KM_DEPT          │",
  "     │               │              │───────────▶│              │",
  "     │               │◀─────────────│◀───────────│              │",
  "     │               │ 拓撲排序 (父部門優先)        │              │",
  "     │               │──[loop 每個部門]─────────────────────────▶│",
  "     │               │              │            │  upsert TsDepartment",
  "     │               │              │            │              │",
  "     │               │──[loop 每個HR員工]──────────────────────▶│",
  "     │               │              │            │  INSERT/UPDATE TsUser",
  "     │               │              │            │  INSERT/UPDATE TsAccount",
  "     │               │              │            │  ensureAccountIdentity",
  "     │               │              │            │  assignRoles (IT→SysAdmin)",
  "     │               │              │            │              │",
  "     │ 完成 (新增N/更新M筆)          │            │              │",
  "     │◀──────────────│              │            │              │",
];

const deployDiagram = [
  "┌──────────────────────── 台水內部網路 ────────────────────────────────┐",
  "│                                                                      │",
  "│  ┌──────────────────────────────────┐                               │",
  "│  │   員工 Browser                    │                               │",
  "│  └──────────────┬───────────────────┘                               │",
  "│                 │ HTTPS:443                                          │",
  "│                 ▼                                                    │",
  "│  ┌──────────────────────────────────────────┐                       │",
  "│  │   JBoss / WildFly 應用伺服器              │                       │",
  "│  │   waterCusSSO.war                        │                       │",
  "│  │   (含 ecpsso.jar, waterHrSync.jar)       │                       │",
  "│  └────┬──────────────┬────────────┬─────────┘                       │",
  "│       │              │            │                                  │",
  "│   JDBC:default   JDBC:km       LDAP:636                             │",
  "│       │              │            │                                  │",
  "│       ▼              ▼            ▼                                  │",
  "│  ┌─────────┐  ┌──────────┐  ┌──────────────────────┐               │",
  "│  │ECP 主DB │  │KM 人事DB │  │ Active Directory      │               │",
  "│  │(讀寫)   │  │(唯讀)    │  │ 網域控制站            │               │",
  "│  └─────────┘  └──────────┘  └──────────────────────┘               │",
  "│  ┌──────────┐                                                        │",
  "│  │客服聊天DB│ ◀── JDBC (唯讀)                                         │",
  "│  └──────────┘                                                        │",
  "└──────────────────────────────────────────────────────────────────────┘",
];

const erDiagram = [
  "┌──────────────┐      ┌──────────────────┐      ┌──────────────┐",
  "│  TsUser      │      │  TsDepartment     │      │  TsAccount   │",
  "│──────────────│      │──────────────────│      │──────────────│",
  "│ FId (PK)     │      │ FId (PK)          │      │ FId (PK)     │",
  "│ FName        │      │ FName             │      │ FLoginName   │",
  "│ FDepartmentId│─────▶│ FParentId (self)  │      │ FPassword    │",
  "│ FEnabled     │      │ FTreeLevel        │      │ FEmail       │",
  "└──────┬───────┘      └──────────────────┘      └──────┬───────┘",
  "       │                                                │",
  "       │        ┌────────────────────┐                 │",
  "       └──────▶ │ TsAccountIdentity  │ ◀───────────────┘",
  "                │────────────────────│",
  "                │ FId (PK)           │",
  "                │ FAccountId (FK)    │",
  "                │ FEntityId (FK)     │",
  "                │ FIdentityTypeId    │",
  "                └────────────────────┘",
  "",
  "┌──────────────┐      ┌──────────────┐      ┌──────────────────────────┐",
  "│  TsRole      │      │  TsRoleUser  │      │  TpCUSmLoginLog           │",
  "│──────────────│      │──────────────│      │──────────────────────────│",
  "│ FId (PK)     │      │ FRoleId (FK) │      │ FId (PK)                 │",
  "│ FName        │◀─────│ FUserId (FK) │      │ U_SessionID              │",
  "└──────────────┘      └──────────────┘      │ U_token                  │",
  "                                             │ FCreateUserId (FK→TsUser)│",
  "                          ┌───────────────── │ FCreateTime  ◀ 需建索引  │",
  "                          │                  └──────────────────────────┘",
  "                          │",
  "         ┌────────────────────────────────┐",
  "         │  TpCUSmChatMessageSummary       │",
  "         │────────────────────────────────│",
  "         │ FId (PK)                       │",
  "         │ U_AgentId / U_AgentName        │",
  "         │ U_ChatId / U_RoomId            │",
  "         │ U_Content                      │",
  "         │ U_SenderId / U_SenderName      │",
  "         │ U_SendTime                     │",
  "         │ U_UserId / U_UserName          │",
  "         └────────────────────────────────┘",
];

// ── document build ───────────────────────────────────────────────────────────
const children = [];

// ══ COVER PAGE ════════════════════════════════════════════════════════════════
children.push(
  new Paragraph({ spacing: { before: 2000 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 800, after: 200 },
    children: [new TextRun({ text: "台灣自來水公司", size: 52, bold: true, font: "微軟正黑體", color: BLUE_DARK })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 100, after: 600 },
    children: [new TextRun({ text: "資訊整合系統", size: 44, bold: true, font: "微軟正黑體", color: BLUE_MID })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { top: { style: BorderStyle.SINGLE, size: 6, color: BLUE_MID } },
    spacing: { before: 80, after: 80 }
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text: "系統架構與詳細設計文件", size: 36, font: "微軟正黑體", color: BLUE_DARK })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE_MID } },
    spacing: { before: 80, after: 600 }
  }),
  new Paragraph({ spacing: { before: 400 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 60 },
    children: [new TextRun({ text: "版本：1.0", size: 24, font: "微軟正黑體" })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: "日期：2026-05-14", size: 24, font: "微軟正黑體" })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: "作者：Lance Wu", size: 24, font: "微軟正黑體" })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: "狀態：UAT v2", size: 24, font: "微軟正黑體" })]
  }),
  pb()
);

// ══ TABLE OF CONTENTS ════════════════════════════════════════════════════════
children.push(
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text: "目錄", font: "微軟正黑體", bold: true, size: 32, color: BLUE_DARK })],
    spacing: { before: 200, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: BLUE_MID, space: 4 } }
  }),
  new TableOfContents("目錄", { hyperlink: true, headingStyleRange: "1-3" }),
  pb()
);

// ══ PART 1: ARCHITECTURE ══════════════════════════════════════════════════════
children.push(h1("第一部分：系統架構圖"));

// 1. System Context
children.push(
  h2("1. 系統整體架構（System Context Diagram）"),
  body("本圖說明台灣自來水公司資訊整合系統與所有外部系統的互動關係，呈現系統邊界與主要使用者。"),
  new Paragraph({ spacing: { before: 120 } }),
  ...systemContextDiagram.map(line =>
    new Paragraph({
      children: [new TextRun({ text: line, size: 16, font: "Courier New" })],
      spacing: { before: 0, after: 0 }
    })
  ),
  new Paragraph({ spacing: { before: 200 } }),
  makeTable(
    ["元件", "說明", "通訊協定"],
    [
      ["內部員工", "使用 ECP 平台的公司員工", "HTTPS / JSON"],
      ["客服人員", "使用客服聊天系統", "Web"],
      ["waterCusSSO", "SSO 單一登入入口（JSP）", "HTTPS / JSON"],
      ["ecpsso.jar", "SSO 登入紀錄核心模組", "Java In-Process"],
      ["waterHrSync.jar", "HR 同步 + 聊天摘要排程", "JDBC / SQL"],
      ["ECP 平台", "主要企業協作平台（外部）", "ECP API / JDBC"],
      ["KM 人事系統", "HR 資料來源（唯讀外部）", "JDBC"],
      ["Active Directory", "LDAP 身分驗證（外部）", "LDAP 389/636"],
      ["客服聊天系統", "聊天資料來源（唯讀外部）", "JDBC"],
    ],
    [3200, 4000, 1826]
  )
);

// 2. Container Diagram
children.push(
  new Paragraph({ spacing: { before: 320 } }),
  h2("2. 容器架構圖（Container Diagram）"),
  body("本圖呈現部署於 JBoss/WildFly 上各 WAR/JAR 元件的內部結構，及其與資料庫的連線關係。"),
  new Paragraph({ spacing: { before: 120 } }),
  ...containerDiagram.map(line =>
    new Paragraph({
      children: [new TextRun({ text: line, size: 16, font: "Courier New" })],
      spacing: { before: 0, after: 0 }
    })
  )
);

// 3. SSO Flow
children.push(
  new Paragraph({ spacing: { before: 320 } }),
  h2("3. SSO 登入流程圖（Sequence Diagram）"),
  body("說明員工帳密登入、後續 SSO Token 驗證，及稽核日誌寫入的完整時序。"),
  new Paragraph({ spacing: { before: 120 } }),
  ...ssoFlowDiagram.map(line =>
    new Paragraph({
      children: [new TextRun({ text: line, size: 16, font: "Courier New" })],
      spacing: { before: 0, after: 0 }
    })
  )
);

// 4. HR Sync Flow
children.push(
  new Paragraph({ spacing: { before: 320 } }),
  h2("4. HR 同步流程圖（Sequence Diagram）"),
  body("說明每日凌晨 02:00 排程觸發的 HR 資料同步十步驟流程。"),
  new Paragraph({ spacing: { before: 120 } }),
  ...hrSyncFlowDiagram.map(line =>
    new Paragraph({
      children: [new TextRun({ text: line, size: 16, font: "Courier New" })],
      spacing: { before: 0, after: 0 }
    })
  )
);

// 5. ER Diagram
children.push(
  new Paragraph({ spacing: { before: 320 } }),
  h2("5. 資料庫 ER 圖"),
  body("呈現 ECP 核心資料表與自訂業務資料表之間的主外鍵關聯。"),
  new Paragraph({ spacing: { before: 120 } }),
  ...erDiagram.map(line =>
    new Paragraph({
      children: [new TextRun({ text: line, size: 16, font: "Courier New" })],
      spacing: { before: 0, after: 0 }
    })
  )
);

// 6. Deploy Diagram
children.push(
  new Paragraph({ spacing: { before: 320 } }),
  h2("6. 部署架構圖"),
  body("說明應用伺服器、資料庫伺服器與 AD 的網路拓撲與連線設定。"),
  new Paragraph({ spacing: { before: 120 } }),
  ...deployDiagram.map(line =>
    new Paragraph({
      children: [new TextRun({ text: line, size: 16, font: "Courier New" })],
      spacing: { before: 0, after: 0 }
    })
  ),
  pb()
);

// ══ PART 2: DESIGN DOCUMENT ════════════════════════════════════════════════════
children.push(h1("第二部分：詳細設計文件"));

// ── Section 1: 專案概述 ──────────────────────────────────────────────────────
children.push(h2("1. 專案概述"));

children.push(h3("1.1 背景"));
children.push(
  body("台灣自來水公司（台水）委託開發一套資訊整合系統，將人事系統（KM）、企業協作平台（ECP）、客服聊天系統三個核心系統整合，達成以下目標："),
  bullet("單一登入（SSO）：員工只需一組帳號即可存取 ECP 平台，透過 Token 機制串接外部系統。"),
  bullet("HR 資料同步：每日自動將 KM 人事系統的員工與部門資料同步至 ECP，保持帳號資料一致性。"),
  bullet("聊天摘要彙整：每日彙整客服聊天記錄，儲存至 ECP 資料庫供後續分析。")
);

children.push(h3("1.2 系統邊界"));
children.push(
  makeTable(
    ["系統", "角色", "擁有方"],
    [
      ["ECP (Quicksilver)", "主要企業協作平台，本系統的部署容器", "Chainsea 鏈鎖科技"],
      ["KM 人事系統", "HR 資料來源（唯讀）", "台水 IT"],
      ["Active Directory", "身分驗證（LDAP）", "台水 IT"],
      ["客服聊天系統", "聊天資料來源（唯讀）", "台水 IT"],
      ["本系統", "整合中介層", "Ai3 / 台水"],
    ],
    [2800, 4200, 2026]
  )
);

children.push(h3("1.3 主要使用者"));
children.push(
  makeTable(
    ["角色", "使用方式"],
    [
      ["內部員工", "透過 SSO 登入 ECP 平台"],
      ["IT 部門", "自動同步帳號，系統管理員角色自動指派"],
      ["客服人員", "聊天記錄自動彙整，無需手動操作"],
    ],
    [3000, 6026]
  )
);

// ── Section 2: 技術堆疊 ──────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("2. 技術堆疊"));
children.push(
  makeTable(
    ["層級", "技術", "版本"],
    [
      ["語言", "Java", "17"],
      ["建置工具", "Maven", "3.x"],
      ["應用框架", "Quicksilver + ECP", "7.1.31.beta22 + 8.5.02.36"],
      ["應用伺服器", "JBoss / WildFly", "（依 ECP 平台版本）"],
      ["前端", "JSP (Jakarta EE)", "4.0"],
      ["Servlet", "Jakarta Servlet", "4.0"],
      ["JSON 處理", "org.json", "20240303"],
      ["日誌", "SLF4J + Log4j2", "2.0.16"],
      ["資料庫", "MariaDB / SQL Server", "（依部署環境）"],
      ["身分驗證", "LDAP / Active Directory", "—"],
      ["部署單元", "WAR + JAR (plugin)", "—"],
    ],
    [2800, 3800, 2426]
  )
);

// ── Section 3: 模組說明 ──────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("3. 模組說明"));

// 3.1 ecpsso
children.push(h3("3.1 ecpsso — SSO 登入紀錄核心模組"));
children.push(
  body("以 ECP Plugin JAR 形式部署，封裝 SSO Token 驗證與登入稽核邏輯。由 waterCusSSO 的 JSP 頁面在執行期呼叫。"),
  new Paragraph({ spacing: { before: 120 } }),
  body("包結構：", { bold: true }),
  ...([
    "com.chainsea.water.ecpsso/",
    "  SSOLoginLogHome.java      ← Service Locator，載入設定、取得服務實體",
    "  model/",
    "    SSOLoginLogModel.java   ← EntityModel 擴展，對應 TpCUSmLoginLog",
    "  dao/",
    "    SSOLoginLogDao.java     ← DAO 介面",
    "    impl/SSOLoginLogDaoImpl.java",
    "  service/",
    "    SSOLoginLogService.java ← Service 介面",
    "    impl/SSOLoginLogServiceImpl.java",
    "  api/impl/SSOLoginLogApiImpl.java  （目前停用）",
    "  action/impl/SSOLoginLogActionImpl.java  （目前停用）",
  ]).map(code),
  new Paragraph({ spacing: { before: 120 } }),
  body("關鍵設計決策：", { bold: true }),
  body("Token 有效期 5 分鐘：getSSOToken() 查詢條件限制在最近 5 分鐘內建立的 Token，防止 Token 被重複使用或長期有效帶來的安全風險。"),
  ...([
    "-- 查詢條件示意",
    "WHERE FCreateTime >= NOW() - INTERVAL 5 MINUTE",
    "  AND U_token = :token AND FCreateUserId = :empId",
  ]).map(code),
  body("Unit ID 隔離：ECP 平台以 Unit ID 區隔不同外掛的資料 Cache Region，ecpsso 使用 df6c8bac-d9ce-4e6c-c404-18fc8f33cec0，Cache Region 為 cus_ssologinlog。"),
  new Paragraph({ spacing: { before: 120 } }),
  body("服務方法：", { bold: true }),
  makeTable(
    ["方法", "說明", "輸入", "輸出"],
    [
      ["doSSO(loginName)", "驗證帳號是否存在於 ECP 並記錄登入", "loginName", "boolean"],
      ["doSSOToken(loginName, token)", "驗證 5 分鐘內的有效 Token", "loginName, token", "boolean"],
      ["checkUser(loginName)", "查詢 TsUser/TsAccount 確認帳號存在", "loginName", "UserInfo"],
      ["addLog(sessionId, token, ...)", "寫入登入稽核記錄", "session 資訊", "void"],
    ],
    [2600, 3200, 1800, 1426]
  )
);

// 3.2 waterCusSSO
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h3("3.2 waterCusSSO — 前端登入入口"));
children.push(
  body("以 WAR 形式部署於 ECP 平台，包含登入頁面（JSP）與 ecpsso.jar 等依賴 JAR。負責接收使用者請求、呼叫 AD 驗證、轉送 SSO Token 驗證。"),
  new Paragraph({ spacing: { before: 120 } }),
  body("login.jsp 端點設計：", { bold: true }),
  makeTable(
    ["項目", "說明"],
    [
      ["HTTP 方法", "POST"],
      ["Content-Type", "application/json"],
      ["CORS", "支援跨域（設有 CORS Header）"],
      ["Request Body", '{ "loginName": "empId or username", "password": "plaintext" }'],
      ["Response", '{ "success": true }'],
    ],
    [2200, 6826]
  ),
  new Paragraph({ spacing: { before: 120 } }),
  body("login.jsp 處理流程：", { bold: true }),
  bullet("解析 JSON 請求體"),
  bullet("呼叫 Quicksilver API 進行 AD/LDAP 驗證"),
  bullet("驗證成功後設定語言 Cookie"),
  bullet("建立 ECP Session"),
  bullet("記錄請求時間戳、來源 IP、使用者名稱至伺服器日誌"),
  new Paragraph({ spacing: { before: 120 } }),
  body("sso.jsp 端點設計：", { bold: true }),
  makeTable(
    ["項目", "說明"],
    [
      ["HTTP 方法", "POST"],
      ["Content-Type", "application/json"],
      ["Request Body", '{ "loginName": "empId", "token": "UUID or custom token" }'],
      ["Response", '{ "success": true / false }'],
    ],
    [2200, 6826]
  ),
  new Paragraph({ spacing: { before: 120 } }),
  body("sso.jsp 處理流程：", { bold: true }),
  bullet("解析 JSON 請求體"),
  bullet("呼叫 SSOLoginLogHome.getService().doSSOToken(loginName, token)"),
  bullet("若 Token 有效 → 回傳成功"),
  bullet("若 Token 失效 → 嘗試 AD Fallback 登入"),
  bullet("寫入日誌至 sso_auth.log")
);

// 3.3 waterHrSync
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h3("3.3 waterHrSync — HR 同步與聊天摘要"));
children.push(
  body("以 ECP Plugin JAR 形式部署，包含兩個子模組："),
  bullet("hrsync：每日凌晨 02:00 將 KM 人事資料同步至 ECP"),
  bullet("chatmessagesummary：每日彙整前一日聊天記錄"),
  new Paragraph({ spacing: { before: 120 } }),
  body("3.3.1 HR 同步子模組", { bold: true, color: BLUE_MID }),
  body("Unit ID：4806684c-e000-3135-6003-1961e9cb6d01"),
  new Paragraph({ spacing: { before: 80 } }),
  body("資料來源：", { bold: true }),
  makeTable(
    ["來源", "說明", "Executor"],
    [
      ["v_KM_USER", "HR 員工 View（部門 ID 以 00 開頭）", "km"],
      ["v_KM_DEPT", "HR 部門 View（含父子關係）", "km"],
    ],
    [2200, 5000, 1826]
  ),
  new Paragraph({ spacing: { before: 120 } }),
  body("欄位對應（v_KM_USER → ECP）：", { bold: true }),
  makeTable(
    ["KM 欄位", "ECP 欄位", "說明"],
    [
      ["EMPLOYEEID", "TsUser.FId (衍生)", "員工編號"],
      ["DISPLAYNAME", "TsUser.FName", "顯示名稱"],
      ["EMAILADDRESS", "TsAccount.FEmail", "電子郵件"],
      ["LOGINID", "TsAccount.FLoginName", "登入帳號"],
      ["DEPARTMENTID", "TsUser.FDepartmentId", "所屬部門"],
    ],
    [2600, 3200, 3226]
  ),
  new Paragraph({ spacing: { before: 120 } }),
  body("syncHrData() 執行步驟：", { bold: true }),
  ...([
    "Step 1:  從 v_KM_USER 讀取 HR 員工清單（dept starts with '00'）",
    "Step 2:  從 v_KM_DEPT 讀取部門清單，拓撲排序後同步至 TsDepartment",
    "Step 3:  建立 HR 員工 LoginId → HrUser 的 Map",
    "Step 4:  讀取現有 ECP TsUser 清單",
    "Step 5:  讀取 IT 部門 ID 清單（部門名稱含「資訊」）",
    "Step 6:  讀取預設角色與 SysAdmin 角色",
    "Step 7:  逐一比對，新增或更新 TsUser / TsAccount",
    "Step 8:  確保 TsAccountIdentity 存在（帳號-人員對應）",
    "Step 9:  指派預設角色；IT 部門額外指派 SysAdmin 角色",
    "Step 10: 記錄同步結果（新增 N 筆 / 更新 M 筆）",
  ]).map(code),
  new Paragraph({ spacing: { before: 120 } }),
  body("角色指派規則：", { bold: true }),
  makeTable(
    ["條件", "角色"],
    [
      ["所有同步員工", "預設角色（hrsync.properties 中設定）"],
      ["部門名稱含「資訊」", "額外指派 SysAdmin 角色"],
    ],
    [3400, 5626]
  ),
  new Paragraph({ spacing: { before: 160 } }),
  body("3.3.2 聊天摘要子模組", { bold: true, color: BLUE_MID }),
  body("Unit ID：4806684c-e000-3135-6003-1961e9cb6d00"),
  new Paragraph({ spacing: { before: 80 } }),
  body("彙整流程：", { bold: true }),
  bullet("GetChatMessageSummaryRountine 觸發（每日執行）"),
  bullet("取得目標日期：Timer args 指定，或預設昨日（LocalDate.now().minusDays(1)）"),
  bullet("ChatMessageSummaryService.getChatMessageSummary(targetDate) 呼叫 DAO"),
  bullet("跨表 JOIN 查詢 TcChatMessage、TrChatSeatStatus、TsUser、TcContact、TcChatMan"),
  bullet("Batch INSERT 寫入 TpCUSmChatMessageSummary")
);

// ── Section 4: 資料庫設計 ──────────────────────────────────────────────────────
children.push(pb());
children.push(h2("4. 資料庫設計"));

children.push(h3("4.1 資料庫連線設定"));
children.push(
  makeTable(
    ["Executor 名稱", "用途", "資料庫"],
    [
      ["default", "ECP 主資料庫（讀寫）", "ECP DB"],
      ["km", "KM 人事系統（唯讀）", "KM DB"],
      ["（預設）", "客服聊天資料庫（唯讀）", "Chat DB"],
    ],
    [2800, 3800, 2426]
  )
);

children.push(h3("4.2 自訂資料表"));

children.push(
  body("TpCUSmLoginLog — SSO 登入稽核：", { bold: true }),
  makeTable(
    ["欄位", "型別", "說明"],
    [
      ["FId", "UUID PK", "主鍵"],
      ["U_SessionID", "VARCHAR", "ECP Session ID"],
      ["U_token", "VARCHAR", "SSO Token"],
      ["FName", "VARCHAR", "登入狀態（LoginStatus）"],
      ["FCreateUserId", "UUID FK", "登入使用者 ID (TsUser)"],
      ["FCreateDepartmentId", "UUID FK", "所屬部門 ID (TsDepartment)"],
      ["U_CreateUserName", "VARCHAR", "登入使用者名稱（冗餘備份）"],
      ["U_CreateDepartment", "VARCHAR", "部門名稱（冗餘備份）"],
      ["FCreateTime", "DATETIME", "建立時間（需建索引，5分鐘查詢關鍵欄位）"],
    ],
    [2800, 1800, 4426]
  ),
  note("FCreateTime 需建立索引，getSSOToken() 的 5 分鐘範圍查詢依賴此欄位效能。"),
  new Paragraph({ spacing: { before: 160 } }),
  body("TpCUSmChatMessageSummary — 聊天摘要：", { bold: true }),
  makeTable(
    ["欄位", "型別", "說明"],
    [
      ["FId", "UUID PK", "主鍵"],
      ["U_AgentId", "VARCHAR", "客服坐席 ID"],
      ["U_AgentName", "VARCHAR", "客服坐席姓名"],
      ["U_ChatId", "VARCHAR", "聊天室 ID"],
      ["U_Content", "TEXT", "訊息內容"],
      ["U_RoomId", "VARCHAR", "聊天房間 ID"],
      ["U_SenderId", "VARCHAR", "發送者 ID"],
      ["U_SenderName", "VARCHAR", "發送者姓名"],
      ["U_SendTime", "DATETIME", "發送時間"],
      ["U_Type", "VARCHAR", "訊息類型"],
      ["U_UserId", "VARCHAR", "客戶使用者 ID"],
      ["U_UserName", "VARCHAR", "客戶使用者姓名"],
    ],
    [2800, 1800, 4426]
  )
);

children.push(h3("4.3 ECP 平台核心資料表（唯讀參考）"));
children.push(
  makeTable(
    ["資料表", "說明"],
    [
      ["TsUser", "ECP 使用者主表"],
      ["TsDepartment", "部門樹狀結構"],
      ["TsAccount", "登入帳號"],
      ["TsAccountIdentity", "帳號 ↔ 人員對應（支援多身分）"],
      ["TsRole", "角色定義"],
      ["TsRoleUser", "角色指派關係"],
    ],
    [3000, 6026]
  )
);

// ── Section 5: API 規格 ────────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("5. API 規格"));

children.push(h3("5.1 Active Endpoints（JSP）"));
children.push(
  body("端點一：POST /sso/ecp/custom/login/login.jsp — 帳密登入", { bold: true }),
  makeTable(
    ["項目", "說明"],
    [
      ["Request Header", "Content-Type: application/json"],
      ["Request Body", '{ "loginName": "string", "password": "string" }'],
      ["Success Response", '{ "success": true }'],
      ["Error Response", '{ "success": false, "message": "帳號或密碼錯誤" }'],
      ["驗證方式", "LDAP bind 至 Active Directory"],
    ],
    [2800, 6226]
  ),
  new Paragraph({ spacing: { before: 160 } }),
  body("端點二：POST /sso/ecp/custom/login/sso.jsp — SSO Token 驗證", { bold: true }),
  makeTable(
    ["項目", "說明"],
    [
      ["Request Body", '{ "loginName": "string", "token": "string" }'],
      ["Success Response", '{ "success": true }'],
      ["Failure Response", '{ "success": false }'],
      ["驗證邏輯", "查詢 TpCUSmLoginLog（5分鐘內），失效則 AD fallback"],
      ["日誌", "寫入 sso_auth.log"],
    ],
    [2800, 6226]
  )
);

children.push(h3("5.2 Disabled Endpoints（暫未啟用）"));
children.push(
  makeTable(
    ["Path", "方法", "說明"],
    [
      ["/TCBEcpSSO/EcpSSO", "POST", "doSSO() ECP API 版本（@Api 標註，isTokenRequired=false）"],
      ["/TCBEcpSSO/SSOToken", "POST", "doSSOToken() ECP API 版本"],
    ],
    [2800, 1200, 5026]
  ),
  note("這些 Endpoint 程式碼已存在但被停用，功能目前由 JSP 直接承擔。")
);

// ── Section 6: 排程設計 ────────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("6. 排程設計"));
children.push(
  makeTable(
    ["排程名稱", "Class", "執行時間", "說明"],
    [
      ["HR 同步", "SyncHrDataRountine", "每日 02:00", "同步人員/部門至 ECP"],
      ["聊天摘要", "GetChatMessageSummaryRountine", "每日（預設昨日）", "彙整前一日聊天記錄"],
    ],
    [2000, 3400, 1800, 1826]
  ),
  new Paragraph({ spacing: { before: 120 } }),
  body("排程約束：", { bold: true }),
  bullet("HR 同步排定在 04:00 備份作業之前執行，確保備份時資料已是最新狀態。"),
  bullet("兩個排程不應同時執行，避免資料庫鎖衝突。"),
  bullet("GetChatMessageSummaryRountine 支援傳入指定日期參數（格式 yyyy-MM-dd）。")
);

// ── Section 7: 安全設計 ────────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("7. 安全設計"));

children.push(h3("7.1 Token 安全"));
children.push(
  makeTable(
    ["機制", "說明"],
    [
      ["有效期限", "Token 5 分鐘後自動失效"],
      ["綁定使用者", "Token 與 empId 綁定，無法跨使用者使用"],
      ["Fallback", "Token 失效時嘗試 AD 重新驗證，而非直接放行"],
      ["稽核日誌", "所有驗證嘗試（成功/失敗）均寫入 TpCUSmLoginLog 與 sso_auth.log"],
    ],
    [2600, 6426]
  )
);

children.push(h3("7.2 密碼安全"));
children.push(
  makeTable(
    ["項目", "說明"],
    [
      ["預設密碼", "儲存於 hrsync.properties，以加密格式儲存（ECP 平台加密機制）"],
      ["AD 驗證", "密碼不落地，由 LDAP bind 操作完成驗證"],
      ["LDAP 連線", "建議使用 LDAPS（636 port）加密傳輸"],
    ],
    [2600, 6426]
  )
);

children.push(h3("7.3 CORS 與資料隔離"));
children.push(
  body("login.jsp 設有 CORS Header 允許跨域請求，應確認 Access-Control-Allow-Origin 的白名單設定（確認是否限定特定網域而非開放 *）。"),
  bullet("KM 人事資料庫使用獨立 Executor（km），僅有讀取權限，無法從 ECP 模組寫入 KM 資料庫。"),
  bullet("聊天資料庫同樣為唯讀存取，確保資料隔離。")
);

// ── Section 8: 錯誤處理與日誌 ──────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("8. 錯誤處理與日誌"));

children.push(h3("8.1 日誌策略"));
children.push(
  makeTable(
    ["日誌", "位置", "內容"],
    [
      ["sso_auth.log", "應用伺服器日誌目錄", "SSO Token 驗證結果、來源 IP、時間戳"],
      ["SLF4J / Log4j2", "ECP 標準日誌", "HR 同步執行結果（新增 N 筆、更新 M 筆）"],
      ["JSP 標準輸出", "伺服器 stdout", "登入請求的時間戳、IP、使用者名稱"],
    ],
    [2400, 2800, 3826]
  )
);

children.push(h3("8.2 HR 同步錯誤處理"));
children.push(
  makeTable(
    ["情境", "處理方式"],
    [
      ["KM DB 連線失敗", "拋出例外，本次同步中止，記錄 ERROR log"],
      ["部門父節點不存在", "拓撲排序保證父節點先建立，若仍失敗則跳過並記錄警告"],
      ["使用者資料衝突", "以 loginName 為唯一鍵，EXISTS 判斷後做 INSERT 或 UPDATE"],
      ["角色指派失敗", "記錄警告，不中止整體同步流程"],
    ],
    [3200, 5826]
  )
);

children.push(h3("8.3 聊天摘要錯誤處理"));
children.push(
  makeTable(
    ["情境", "處理方式"],
    [
      ["無聊天記錄", "返回空集合，不執行 INSERT，記錄 INFO log"],
      ["資料重複插入", "以 FId UUID 為主鍵，重跑時若 FId 重複會拋 PK 違反例外"],
    ],
    [3200, 5826]
  ),
  note("聊天摘要模組目前缺乏冪等設計，若 Timer 重複執行可能造成重複資料。建議加入執行前先刪除當日資料的機制（DELETE + INSERT）或改用 UPSERT。")
);

// ── Section 9: 部署與設定 ────────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("9. 部署與設定"));

children.push(h3("9.1 部署步驟"));
children.push(
  ...([
    "1. 編譯 ecpsso      → 產生 ecpsso.jar",
    "2. 編譯 waterHrSync → 產生 waterHrSync.jar",
    "3. 將 JAR 複製至 waterCusSSO/WEB-INF/lib/",
    "4. 打包 waterCusSSO → 產生 waterCusSSO.war",
    "5. 部署 WAR 至 JBoss/WildFly",
    "6. 在 ECP 後台設定 Timer Routine（HR sync 02:00、Chat summary 每日）",
  ]).map(code)
);

children.push(h3("9.2 hrsync.properties 設定"));
children.push(
  ...([
    "# TsAccountIdentity 使用的身分類型 UUID（請勿任意修改）",
    "accountIdentityTypeId=564cf69e-76d6-4baf-b584-6e04c2911dae",
    "",
    "# 新建帳號的預設密碼（ECP 加密格式）",
    "accountDefaultPassword=<encrypted>",
    "",
    "# ECP 部門樹根節點 UUID",
    "TsDepartmentRootFId=00000000-0000-0000-1001-000000000001",
  ]).map(code)
);

children.push(h3("9.3 資料庫 Executor 設定（ECP 後台）"));
children.push(
  makeTable(
    ["Executor", "對應資料庫", "備註"],
    [
      ["default", "ECP 主資料庫", "讀寫"],
      ["km", "KM 人事資料庫", "唯讀"],
    ],
    [2400, 4200, 2426]
  )
);

children.push(h3("9.4 環境需求"));
children.push(
  makeTable(
    ["項目", "需求"],
    [
      ["Java", "17+"],
      ["JBoss/WildFly", "ECP 8.5 相容版本"],
      ["ECP", "8.5.02.36"],
      ["Quicksilver", "7.1.31.beta22"],
      ["網路", "應用伺服器可連線至 AD、KM DB、Chat DB"],
    ],
    [3000, 6026]
  )
);

// ── Section 10: 已知限制 ────────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 240 } }));
children.push(h2("10. 已知限制與待辦事項"));

children.push(h3("10.1 已知限制"));
children.push(
  makeTable(
    ["項目", "說明"],
    [
      ["API 端點停用", "SSOLoginLogApi 的 ECP API 端點目前為空實作，功能由 JSP 承擔"],
      ["無 Token Revoke 機制", "Token 無法主動撤銷，只能等待 5 分鐘自然過期"],
      ["聊天摘要非冪等", "重複執行會產生重複資料"],
      ["CORS 白名單", "login.jsp 的 CORS 設定需確認是否鎖定特定來源域名"],
      ["帳號停用邏輯", "KM 人員離職後，ECP 帳號的停用/刪除流程未在程式碼中看到，可能需要手動處理"],
    ],
    [3200, 5826]
  )
);

children.push(h3("10.2 建議改善項目"));
children.push(
  makeTable(
    ["優先級", "項目", "說明"],
    [
      ["高", "聊天摘要冪等設計", "執行前先 DELETE 當日資料，或改用 UPSERT"],
      ["高", "帳號離職停用", "增加「HR 中不存在的 ECP 帳號自動停用」邏輯"],
      ["中", "Token 延長機制", "提供 refresh token 或延長有效期至 30 分鐘"],
      ["中", "CORS 白名單", "限制 Access-Control-Allow-Origin 為特定域名"],
      ["低", "API 端點啟用", "啟用 ECP API 版本的 SSO 端點，取代 JSP 直接處理"],
      ["低", "單元測試", "補充 HrSyncService、SSOLoginLogService 的單元測試"],
    ],
    [1200, 2800, 5026]
  )
);

// ── footer note ────────────────────────────────────────────────────────────────
children.push(
  new Paragraph({ spacing: { before: 400 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { top: { style: BorderStyle.SINGLE, size: 4, color: GRAY_LINE, space: 4 } },
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text: "本文件依據原始碼分析產生，如有疑義請以原始碼為準。", size: 18, font: "微軟正黑體", color: "808080" })]
  })
);

// ── document assembly ─────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "●",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }]
      }
    ]
  },
  styles: {
    default: {
      document: { run: { font: "微軟正黑體", size: 20 } }
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "微軟正黑體", color: BLUE_DARK },
        paragraph: { spacing: { before: 480, after: 160 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "微軟正黑體", color: BLUE_MID },
        paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 1 }
      },
      {
        id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "微軟正黑體" },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 2 }
      },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: PAGE_H },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE_MID, space: 4 } },
          spacing: { after: 80 },
          children: [new TextRun({ text: "台灣自來水公司 資訊整合系統 — 系統架構與詳細設計文件", size: 16, font: "微軟正黑體", color: "808080" })]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: GRAY_LINE, space: 4 } },
          spacing: { before: 80 },
          children: [
            new TextRun({ text: "第 ", size: 16, font: "微軟正黑體", color: "808080" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "微軟正黑體", color: "808080" }),
            new TextRun({ text: " 頁", size: 16, font: "微軟正黑體", color: "808080" }),
          ]
        })]
      })
    },
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("docs/台水資訊整合系統_設計文件.docx", buffer);
  console.log("Done: docs/台水資訊整合系統_設計文件.docx");
});
