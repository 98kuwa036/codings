# GAS Web App Projects - Comprehensive Technical Analysis

## Executive Summary

This analysis covers three interconnected Google Apps Script (GAS) web applications implementing an intake/delivery record management system with multi-tiered authentication and admin dashboard:

1. **loginform** - Centralized authentication gateway
2. **Intake-delivery-record** - Main data entry and recording application
3. **Admin-Page** - Administrative dashboard for data management

---

## PROJECT 1: LOGINFORM (Authentication Service)

### Overview
Central login gateway for the system. Handles user authentication and credential management, generates signed authentication tokens, and redirects users to appropriate applications.

### Directory Structure
```
loginform/
├── Code.gs           # Main entry point (doGet, doPost)
├── Auth.gs           # Authentication functions
├── Config.gs         # Configuration management
├── Cache.gs          # Caching utilities
├── Utils.gs          # General utilities
├── index.html        # Login form UI
├── JavaScript.html   # Client-side logic
└── Style.html        # CSS styling
```

### Implemented Features

#### A. User Management
- **Register/Link IDs**: Associate new user IDs with existing staff member names
- **Password Management**: Set and change passwords with hashing
- **User Deletion**: Remove user accounts from the system
- **User Data Retrieval**: Fetch all users from managed spreadsheet

#### B. Authentication
- **Login Form**: Standard ID/password input with form validation
- **Password Hashing**: SHA-256 with per-user salt
- **Token Generation**: Creates signed JWT-style tokens with expiration (4 hours default)
- **Client Redirect Handling**: Routes authenticated users to either Record App or Admin App

#### C. User Info Editing Section
- Dynamic form that switches between three modes:
  1. Register/Link new ID to staff member
  2. Change password for existing ID
  3. Delete user account
- Real-time validation with half-width character conversion
- Dropdown population from unlinked staff members

### Authentication Mechanisms

#### Password Security
- **Hashing Algorithm**: SHA-256 (Utilities.computeDigest)
- **Salt**: Per-user UUID (Utilities.getUuid)
- **Storage**: Hash + Salt stored separately in spreadsheet columns C & E
- **Validation**: Client-side half-width enforcement + server-side input validation

#### Token Generation
```
Token Structure:
- Payload: Base64URL(JSON({uid, iat, exp}))
- Signature: HMACSHA256(payload, TOKEN_SECRET_KEY)
- Nonce (n_rec): UUID for Record App (one-time use)
- Nonce (n_adm): UUID for Admin App (one-time use)
- Expiration: 4 hours (14400 seconds)
```

#### Security Parameters
- **TOKEN_SECRET_KEY**: Shared with Record App and Admin App (256-character complex string)
- **URL Parameters**: All token components encoded with encodeURIComponent to prevent Base64 character corruption (+, /, =)
- **Redirect Flag**: Whitelisted to 'admin' or 'record' (default: 'record')

### Code Patterns Used

1. **Template-based HTML Rendering**
   ```javascript
   const template = HtmlService.createTemplateFromFile('index');
   template.redirectFlag = redirectFlag;
   template.scriptUrl = ScriptApp.getService().getUrl();
   return template.evaluate();
   ```

2. **Configuration Loading Pattern**
   ```javascript
   if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
     loadConfig_();
   }
   ```

3. **Client-side Validation with Real-time Feedback**
   - Full-width to half-width character conversion
   - Input sanitization on blur/input events
   - Error message display in reserved height containers

4. **Caching for Performance**
   - Script cache for user data (1-hour TTL)
   - Cache invalidation on data changes
   - Fallback to spreadsheet if cache miss

5. **Form State Management**
   - DOM element caching in global `dom` object
   - Section toggle between login and registration modes
   - Disabled state management during async operations

### Data Flow to Other Projects

**To Intake-delivery-record:**
```
Login Success → Generate Token (p, s, uid, n_rec, n_adm)
              → Redirect to: RECORD_APP_URL?p=...&s=...&uid=...&n_rec=...&n_adm=...
```

**To Admin-Page:**
```
Admin Flag → Generate Token (p, s, uid, n_adm)
          → Redirect to: ADMIN_APP_URL?p=...&s=...&uid=...&n_adm=...
```

### Configuration

**Key Settings:**
- `SPREADSHEET_ID`: Shared data store (ユーザー管理 sheet)
- `TOKEN_SECRET_KEY`: HMACSHA256 signing key (shared)
- `RECORD_APP_URL`: Deployment URL of Intake-delivery-record
- `ADMIN_APP_URL`: Deployment URL of Admin-Page
- `TOKEN_EXPIRATION`: 14400 seconds (4 hours)
- `CACHE_EXPIRATION`: 3600 seconds (1 hour)
- `SYSTEM_NAME`: "入出庫登録ツール"

**Sheet Requirements:**
- Sheet Name: 'ユーザー管理'
- Columns: A(Name), B(ID), C(Hash), D(unused), E(Salt), F(Role)

---

## PROJECT 2: INTAKE-DELIVERY-RECORD (Main Application)

### Overview
Core data entry and recording application for intake/delivery operations. Handles user authentication validation, data collection, file uploads with OCR processing, and integrates with the admin dashboard.

### Directory Structure
```
Intake-delivery-record/
├── Code.gs                    # Main router (doGet, doPost)
├── Auth.gs                    # Token & Nonce validation
├── Config.gs                  # Configuration management
├── Utils.gs                   # Logging, user info retrieval
├── Api_Client.gs              # Client API handlers
├── ExternalApi.gs             # Vision API, Drive integration
├── Trigger_Cache.gs           # Cache management & triggers
├── PageVersion.html           # Main data entry UI
├── ErrorPage.html             # Error display
├── JavaScript_Main.html       # Main UI logic
├── JavaScript_Api.html        # API communication logic
├── JavaScript_UI.html         # UI helper functions
└── Style.html                 # CSS styling
```

### Implemented Features

#### A. Authentication & Session Management
- **Token Validation**: HMACSHA256 signature verification
- **Nonce Validation**: One-time use UUID tracking via cache
- **Expiration Checking**: Token timestamp validation
- **Multi-route Handling**: Router logic directing authenticated/unauthenticated users
- **Session Timeout**: Automatic logout on token expiration

#### B. Data Entry & Recording
- **Registrant Selection**: Dropdown of authorized users
- **Date/Time Selection**: Date picker for transaction date
- **Mode Toggle**: Inbound (入庫) / Outbound (出庫) modes
- **Item Entry**: Dynamic item list with:
  - Item selection from product master
  - Quantity input
  - Add/remove capability
- **Bulk Operations**: Multi-item submission in single transaction

#### C. File Upload & OCR Processing
- **Resumable Upload**: Two-stage Google Drive upload process
  - Temporary folder storage during processing
  - Final folder storage after validation
- **Vision OCR Integration**: Extract text from uploaded images (Japanese text hints)
- **File Management**:
  - Automatic filename generation: YYYY-MM-DD_HHMM_REGISTRANT_VOUCHERNUMBER.ext
  - Preserve original file extension
  - Safe character conversion for names

#### D. Temporary Item Registration
- **Approval Workflow**: Submit items pending admin approval
- **Queue Management**: Store pending items in "一時作業" sheet
- **Status Tracking**: Pending → Approved/Rejected workflow

#### E. Cache & Performance Management
- **UI Settings Cache**: 1-hour TTL for form visibility settings
- **Dropdown Cache**: 1-hour TTL for user and product lists
- **Webhook Integration**: Admin page notifies when data updates
- **Edit Triggers**: Automatic cache invalidation on spreadsheet changes

### Authentication/Security Mechanisms

#### Token Validation Flow
```
1. Extract URL params: p (payload), s (signature), n_rec (nonce), n_adm (admin nonce)
2. Verify signature: HMACSHA256(p) == s
3. Decode payload: JSON({uid, iat, exp})
4. Check expiration: now < payload.exp
5. Validate nonce: n_rec not previously used (cache check)
6. Extract uid from token payload
```

#### Nonce Management
- **Purpose**: Prevent replay attacks and limit URL reusability
- **Storage**: ScriptCache with 10-minute TTL
- **Consumption**: One-time use flag set on first access
- **Recovery**: Users must re-authenticate via login form

#### Authorization Flow
```
doGet(e)
  ├─ No params → routeToLoginPage()
  ├─ Has n_rec → routeToRecordTool() [main data entry]
  └─ Has n_adm → routeToLoginPage(authenticated=true) [back to login as admin view]
```

### Code Patterns Used

#### 1. Configuration-Driven Architecture
```javascript
if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
  loadConfig_();
}
const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
const sheet = ss.getSheetByName(CONFIG.SHEETS.HISTORY);
```

#### 2. Lock-Based Concurrency Control
```javascript
const lock = LockService.getScriptLock();
if (!lock.tryLock(10000)) {
  throw new Error("Server busy, try again");
}
try {
  // Write data
} finally {
  lock.releaseLock();
}
```

#### 3. Webhook-Driven Cache Invalidation
```javascript
// In doPost (webhook receiver)
removeCacheByType_(payload.updateType);

// In Admin_Utils.gs (webhook sender)
UrlFetchApp.fetch(RECORD_APP_WEBHOOK_URL, {
  method: 'post',
  payload: JSON.stringify({
    secret: WEBHOOK_SECRET,
    updateType: 'dropdown_data'
  })
});
```

#### 4. Multi-Stage File Upload
```javascript
// Get resumable upload URL
const { uploadUrl, fileId } = getResumableUploadUrl(fileName, mimeType);

// Client performs resumable upload
// Server finalizes:
const file = DriveApp.getFileById(fileId);
file.setName(newName);
file.moveTo(DriveApp.getFolderById(FINAL_FOLDER_ID));
```

#### 5. Logging Pattern
```javascript
writeLog_([message1, message2], {
  functionName: "acceptRegistrationData",
  status: "Success",
  message: "User-facing message",
  editorName: currentUserInfo.name
});
```

### Data Flow

#### Data Recording to Spreadsheet
```
acceptRegistrationData()
  ├─ Validate user & nonce
  ├─ Process file upload (if present)
  │  ├─ Rename file: YYYY-MM-DD_HHMM_REGISTRANT_VOUCHERNUMBER.ext
  │  ├─ Move to final folder
  │  └─ Get shareable URL
  ├─ Insert rows to HISTORY sheet (A-G columns):
  │  ├─ Column A: Timestamp
  │  ├─ Column B: Mode (inbound/outbound)
  │  ├─ Column C: Date
  │  ├─ Column D: Registrant
  │  ├─ Column E: Item name
  │  ├─ Column F: Quantity
  │  └─ Column G: File URL (if applicable)
  └─ Return success message
```

#### Cache Update via Webhook
```
Admin Page Updates Master/User Sheet
  → notifyRecordApp_('dropdown_data')
  → POST to RECORD_APP_WEBHOOK_URL
  → RECORD_APP receives in doPost()
  → removeCacheByType_('dropdown_data')
  → Cache invalidated for next request
```

### Integration Points

**From loginform:**
- Token validation (p, s parameters)
- Nonce validation (n_rec parameter)
- User role/name retrieval from shared User Management sheet

**To Admin-Page:**
- Admin link generation with separate nonce (n_adm)
- Allows admin to return to record app

**Shared Resources:**
- Spreadsheet: ユーザー管理, マスター, 入出庫記録, 一時作業, 実行ログ, UI_Settings sheets
- TOKEN_SECRET_KEY: HMACSHA256 signing
- WEBHOOK_SECRET: For admin notifications

### Configuration

**Critical Settings:**
- `LOGIN_APP_URL`: Redirect for unauthorized access
- `ADMIN_PAGE_URL`: Admin dashboard URL (for link generation)
- `TOKEN_SECRET_KEY`: Token signing (shared with login & admin)
- `WEBHOOK_SECRET`: Admin notification authentication
- `VISION_API_KEY`: Google Cloud Vision API key
- `TEMP_DRIVE_FOLDER_ID`: Staging folder for uploads
- `FINAL_DRIVE_FOLDER_ID`: Final storage folder
- `NONCE_CACHE_EXPIRATION`: 600 seconds (10 minutes)

**Sheet Requirements:**
- 'ユーザー管理': User list for dropdown (Column A: Name, Column B: ID, Column F: Role)
- 'マスター': Product/item master (Column A: Code, Column B: Name, Column C: Category, Column D: Status)
- '入出庫記録': Transaction history (7 columns for recording data)
- '一時作業': Pending item approval queue (6 columns: Timestamp, Code, Name, Category, Registrant, Status)
- 'UI_Settings': Form visibility toggles (Columns A: Key, B: Value)
- '実行ログ': Audit trail (4 columns: Timestamp, Function, Status, Message)

---

## PROJECT 3: ADMIN-PAGE (Administration Dashboard)

### Overview
Administrative interface for managing users, products/items, handling item approvals, and configuring system settings. Implements two-factor authentication (2FA) for SuperAdmin role access.

### Directory Structure
```
Admin-Page/
├── Admin_Code.gs              # Main entry point (doGet)
├── Admin_Auth.gs              # Token validation, 2FA
├── Admin_Config.gs            # Configuration management
├── Admin_Data.gs              # CRUD operations
├── Admin_Approval.gs          # Item approval workflow
├── Admin_Setting.gs           # UI/permission settings
├── Admin_Utils.gs             # Logging, webhooks
├── AdminPage.html             # Admin dashboard UI
├── CodeEntryPage.html         # 2FA code entry form
├── CodeEntryJavaScript.html   # 2FA logic
├── ErrorPage.html             # Error display
└── (CSS styling embedded in HTML)
```

### Implemented Features

#### A. Authentication with 2FA
- **Token Validation**: Same HMACSHA256 verification as Record App
- **Role-Based Access**: SuperAdmin requires 2FA, others allowed direct access
- **2FA Flow**:
  1. SuperAdmin login attempt triggers email code generation
  2. Code sent to script deployer's email (Session.getEffectiveUser())
  3. 5-minute code validity window
  4. After code verification, sets 1-hour auth flag
- **Code Storage**: Script cache with 5-minute TTL
- **Auth Flag**: Script cache with 1-hour TTL

#### B. User Management (CRUD)
- **Create**: Add new users with name, ID, password, role, status
- **Read**: Display all users with sortable columns
- **Update**: Edit user information and role assignments
- **Delete**: Remove user accounts
- **Roles**: Configurable (e.g., SuperAdmin, Admin, User)
- **Status**: Track active/inactive status

#### C. Product/Item Master Management (CRUD)
- **Create**: Add products with code, name, category, status
- **Read**: View master list with filtering
- **Update**: Modify product details
- **Delete**: Remove products
- **Auto-numbering**: Category-based ID generation (A001, B001, C001, etc.)
- **Category Prefixes**:
  - A: 劇薬薬品 (Controlled drugs)
  - B: 普通薬品 (Regular drugs)
  - C: 治療用資材 (Treatment materials)
  - D: 繁殖用資材 (Breeding materials)
  - E: 点滴用資材 (Drip materials)
  - F: 飼料添加物 (Feed additives)
  - G: 消耗品 (Consumables)
  - H: その他 (Other)

#### D. Item Approval Workflow
- **Pending Items**: Review items submitted for approval from Record App
- **Approve**: Move pending item to Master with auto-generated ID
- **Reject**: Mark item as rejected
- **Workflow State Machine**:
  - Pending → Approved (moved to Master, cache invalidated)
  - Pending → Rejected (status updated)
  - Master appears in Record App dropdown after approval

#### E. Settings Management
- **UI Visibility Settings**: Toggle form element visibility
  - Photo upload visible
  - Voucher number visible
  - Registrant visible
  - Date visible
  - Mode toggle visible
  - Item add visible
  - Item list visible
- **Role-Based Permissions**: Configure page access per role
  - PageA (User Management)
  - PageB (Master Management)
  - PageC (Log Viewing)
  - PageD (Settings)
  - PageE (UI Configuration)
  - PageF (Approval Workflow)
  - PageG (Permission Management)
- **Real-time Sync**: Webhook notifies Record App of setting changes

#### F. Audit Logging
- **Comprehensive Logging**: All operations logged with timestamp, editor, function, status
- **Log Retention**: Keep 500 most recent entries
- **Log Columns**: Timestamp, Log Type (admin), Editor Name, Function Name, Status, Message

### Authentication/Security Mechanisms

#### Token Verification
```
verifyTokenFromUrl(params)
  ├─ Check p, s, uid, n_adm parameters present
  ├─ Verify signature: HMACSHA256(p) == s
  ├─ Decode & validate payload structure
  ├─ Check token expiration
  ├─ Get user role from ユーザー管理 sheet (Column F)
  ├─ Validate nonce (n_adm):
  │  ├─ If new nonce (not in cache):
  │  │  └─ If SuperAdmin → require_2fa
  │  │  └─ Else → success (direct access)
  │  └─ If used nonce (in cache):
  │     └─ Check if 2FA flag exists
  │        ├─ If yes → success (2FA passed)
  │        └─ If no → error (replay attack)
  └─ Return auth result with status
```

#### 2FA Implementation
```
send2FACode(uid, userName)
  ├─ Generate 6-digit code
  ├─ Store in cache with 5-minute TTL
  ├─ Email code to script deployer
  └─ Return success

verifyCode(uid, code, userName)
  ├─ Retrieve cached code
  ├─ Compare with user input
  ├─ If match:
  │  ├─ Delete code from cache
  │  ├─ Set 2FA flag (1-hour TTL)
  │  └─ Return success
  └─ If no match → Return error
```

#### Role-Based Access Control
- **SuperAdmin**: 
  - Full access to all pages
  - Requires 2FA on login
  - Cannot modify own permissions
- **Admin**: 
  - Access configurable per page
  - No 2FA requirement
  - Can manage users and products
- **User**: 
  - Limited access
  - No admin privileges
  - View-only for most pages

### Code Patterns Used

#### 1. Centralized Config Loading
```javascript
function ensureConfigLoaded_() {
  if (!ADMIN_CONFIG.SHEETS) {
    loadAdminConfig_();
  }
}
```

#### 2. Lock-Protected Operations
```javascript
const lock = LockService.getScriptLock();
if (!lock.tryLock(10000)) {
  throw new Error("Server busy");
}
try {
  // Perform locked operation
} finally {
  lock.releaseLock();
}
```

#### 3. Webhook Notification Pattern
```javascript
// After data modification
notifyRecordApp_('dropdown_data'); // or 'ui_settings'

// Webhook sends:
{
  secret: WEBHOOK_SECRET,
  updateType: updateType
}
```

#### 4. Auto-ID Generation
```javascript
generateNewManagementId(categoryName)
  ├─ Get prefix from categoryName (e.g., "劇薬薬品" → "A")
  ├─ Find max numeric suffix for prefix in Master sheet
  ├─ Return prefix + padded number (e.g., "A001", "A002")
```

#### 5. Audit Logging
```javascript
writeLog_([logMessages], {
  functionName: "updateUserData",
  status: "Success",
  message: "User [name] updated",
  editorName: userName
});
// Logs to 実行ログ sheet with 6-column format
```

### Data Persistence

#### User Management Sheet ('ユーザー管理')
```
Columns: A(Name), B(ID), C(Password), D(unused), E(unused), F(Role), G(Status)
Row 1: Headers
Row 2+: User data
```

#### Master Sheet ('マスター')
```
Columns: A(Code), B(Name), C(Category), D(Status)
Row 1: Headers
Row 2+: Product data
```

#### Approval Queue ('一時作業')
```
Columns: A(Timestamp), B(Code), C(Name), D(Category), E(Registrant), F(Status)
Row 1: Headers
Row 2+: Pending items (Status: Pending/Approved/Rejected)
```

#### Log Sheet ('実行ログ')
```
Columns: A(Timestamp), B(Log Type), C(Editor), D(Function), E(Status), F(Message)
Row 1: Headers
Row 2+: Log entries (max 500 rows)
```

### Integration Points

**From loginform:**
- Receives authenticated token (p, s, uid, n_adm)
- Verifies TOKEN_SECRET_KEY matches

**To Intake-delivery-record:**
- Notifies via webhook when Master or User data changes
- Sends update type: 'dropdown_data' or 'ui_settings'
- Record app invalidates cache and re-fetches

**Shared Resources:**
- Spreadsheet with 6 managed sheets
- TOKEN_SECRET_KEY for JWT verification
- WEBHOOK_SECRET for notification authentication
- PropertiesService for role settings & configuration

### Configuration

**Essential Settings:**
- `TOKEN_SECRET_KEY`: Shared JWT signing key
- `SPREADSHEET_ID`: Central data store
- `LOGIN_PAGE_URL`: Redirect for re-authentication
- `RECORD_APP_WEBHOOK_URL`: Notification endpoint
- `WEBHOOK_SECRET`: Webhook authentication
- `SYSTEM_NAME`: "管理者ダッシュボード"

---

## CROSS-PROJECT DATA FLOW & ARCHITECTURE

### System Architecture Diagram

```
                    ┌─────────────────┐
                    │   loginform     │
                    │ (Auth Gateway)  │
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │                         │
        Token + n_rec            Token + n_adm
                │                         │
                v                         v
    ┌──────────────────────┐  ┌─────────────────────┐
    │ Intake-delivery-     │  │   Admin-Page        │
    │ record (Main App)    │  │ (Admin Dashboard)   │
    └────────────┬─────────┘  └──────────┬──────────┘
                 │                       │
                 │  (Webhook)            │
                 │  dropdowns updated    │ (Returns to Record via n_adm)
                 │  UI settings changed  │
                 │                       │
                 └───────────────────────┘
                 
                 ┌──────────────────────┐
                 │  Shared Spreadsheet  │
                 │ - ユーザー管理       │
                 │ - マスター           │
                 │ - 入出庫記録         │
                 │ - 一時作業           │
                 │ - UI_Settings        │
                 │ - 実行ログ           │
                 └──────────────────────┘
```

### Authentication Token Flow

```
User Login
  ↓
[loginform] checkLogin(id, password)
  ├─ Validate credentials (SHA256 hash check)
  ├─ Generate JWT-style token:
  │  ├─ Payload: Base64URL({uid, iat, exp})
  │  ├─ Signature: HMACSHA256(payload, TOKEN_SECRET_KEY)
  │  ├─ Nonce (n_rec): UUID for Record App
  │  └─ Nonce (n_adm): UUID for Admin App
  ├─ Build redirect URL with query parameters
  └─ Return redirectUrl

User clicks button
  ↓
Redirect to destination (Record or Admin)
  ↓
[destination] validateToken(p, s, n_rec/n_adm)
  ├─ Verify signature matches
  ├─ Decode and validate payload
  ├─ Check expiration
  ├─ Validate nonce (one-time use)
  ├─ Retrieve user role
  └─ Grant access or request 2FA (Admin only)

[Admin] if SuperAdmin
  ├─ Generate 6-digit code
  ├─ Email to script deployer
  ├─ Show code entry form
  ├─ On correct code:
  │  ├─ Set 2FA flag in cache (1 hour)
  │  └─ Grant access
  └─ After 1 hour or next login: Require 2FA again
```

### Data Update Flow (Admin → Record)

```
Admin modifies Master or User sheet
  ↓
[Admin] notifyRecordApp_('dropdown_data' or 'ui_settings')
  ├─ Prepare webhook payload:
  │  ├─ secret: WEBHOOK_SECRET
  │  └─ updateType: 'dropdown_data' or 'ui_settings'
  └─ POST to RECORD_APP_WEBHOOK_URL

[Record App] doPost(e)
  ├─ Verify webhook secret
  ├─ Call removeCacheByType_(updateType)
  │  ├─ Delete CACHE_KEY_PREFIX_DROPDOWN_
  │  └─ (or CACHE_KEY_PREFIX_UI_)
  └─ Return success

[Record App Client] on next data fetch
  ├─ Call getInitialData()
  ├─ getDropdownData_() checks cache
  │  ├─ Cache miss → Read fresh from Master/User sheets
  │  └─ Populate dropdown with new items
  └─ Display updated lists to user
```

### File Upload & OCR Flow

```
User selects image file
  ↓
[Browser] Client-side:
  ├─ Read file as Base64
  ├─ Call getResumableUploadUrl()
  ├─ Receive uploadUrl from [Record App]
  └─ Perform resumable upload to uploadUrl

[Record App] acceptRegistrationData(formData, fileId)
  ├─ Lock concurrent operations
  ├─ Get file from temp folder
  ├─ Rename: YYYY-MM-DD_HHMM_REGISTRANT_VOUCHERNUMBER.ext
  ├─ Move to final folder
  ├─ Insert row to HISTORY sheet with file URL
  ├─ Optionally call runOCR() on image:
  │  ├─ Base64 image → Vision API
  │  ├─ Vision returns detected text
  │  └─ Text available for item name prefilling
  └─ Return success

[Browser] Show confirmation
  └─ User can continue entering more records
```

### Shared Data Resources

#### Configuration Values (PropertiesService)
All three apps share these via UserProperties:

```
- TOKEN_SECRET_KEY: "yIm43SkRO#Oeq_Gg2smY8EVAx3FJ=TkQA?QiCdhWWn-#PU]nHyD-0jpcYn1KYwA["
- SPREADSHEET_ID: "1h3MNEOKWeOIzHvGcrPIF1rR9nBoP668xZO-C8pq_3As"
- WEBHOOK_SECRET: "2qjuVWevemyd2UBjYYYdgh4rrdVJhbu2D"
- SYSTEM_NAME: "入出庫登録ツール" / "管理者ダッシュボード"
- SHEETS_CONFIG_JSON: {MASTER, USER, HISTORY, PROCESSING_QUEUE, LOG, UI_SETTINGS}
- Various folder IDs, API keys, URLs
```

#### Primary Spreadsheet Sheets

1. **ユーザー管理 (User Management)**
   - Row 1: Headers (Name, ID, Hash, ?, Salt, Role, Status)
   - Rows 2+: User accounts
   - Used by: All apps for authentication and dropdown population

2. **マスター (Product Master)**
   - Row 1: Headers (Code, Name, Category, Status)
   - Rows 2+: Product/item definitions
   - Used by: Record app (dropdown), Admin for CRUD

3. **入出庫記録 (Transaction History)**
   - Row 1: Headers (Timestamp, Mode, Date, Registrant, Item, Quantity, FileURL)
   - Rows 2+: Recorded transactions
   - Used by: Record app (writes), Admin (views)

4. **一時作業 (Processing Queue)**
   - Row 1: Headers (Timestamp, Code, Name, Category, Registrant, Status)
   - Rows 2+: Items pending approval
   - Used by: Record app (inserts temp items), Admin (approves/rejects)

5. **UI_Settings**
   - Row 1: Headers (Key, Value)
   - Rows 2+: Form visibility toggles
   - Used by: Record app (show/hide form elements), Admin (configure)

6. **実行ログ (Execution Log)**
   - Row 1: Headers (Timestamp, LogType, Editor, Function, Status, Message)
   - Rows 2+: Audit trail
   - Used by: All apps for logging, Admin views in dashboard

---

## KEY SECURITY FEATURES

### 1. Token-Based Authentication
- JWT-style payload + HMACSHA256 signature
- 4-hour token expiration
- No plaintext passwords in URLs
- Separate nonces for Record and Admin access

### 2. Nonce/Replay Attack Prevention
- One-time use UUIDs (n_rec, n_adm)
- Cached after first use
- 10-minute validity window in Record App
- Prevents URL replay attacks

### 3. Two-Factor Authentication (Admin Only)
- Email-based code delivery
- 5-minute code validity
- 1-hour auth flag after verification
- SuperAdmin-only requirement

### 4. Password Security
- SHA-256 hashing with per-user salt
- Salt stored separately from hash
- Client-side half-width validation
- Server-side input validation

### 5. Role-Based Access Control
- SuperAdmin, Admin, User roles
- Page-level permission configuration
- 2FA enforcement based on role
- Audit logging of all admin actions

### 6. Webhook Security
- Shared secret (WEBHOOK_SECRET) authentication
- POST requests authenticated via secret comparison
- Used only for internal admin→record notifications

### 7. Concurrency Control
- LockService for database write operations
- Prevents race conditions on file moves
- 10-second lock timeout

### 8. Data Isolation
- Proper URL encoding of Base64 characters
- HTML template escaping
- No SQL injection risk (Sheets API, not SQL)

---

## KEY CODE PATTERNS ACROSS PROJECTS

### 1. Configuration Management Pattern
```javascript
if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
  loadConfig_();
}
const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
```
**Used in:** All three projects
**Purpose:** Lazy load configuration on demand

### 2. Caching Pattern
```javascript
const cache = CacheService.getScriptCache();
const cached = cache.get(CACHE_KEY);
if (cached) return JSON.parse(cached);
// ... fetch from sheet
cache.put(CACHE_KEY, JSON.stringify(data), TTL);
```
**Used in:** Record App (dropdowns, UI settings)
**Purpose:** Reduce spreadsheet API calls

### 3. Lock-Protected CRUD
```javascript
const lock = LockService.getScriptLock();
if (!lock.tryLock(10000)) throw new Error("Server busy");
try {
  // Perform write operation
} finally {
  lock.releaseLock();
}
```
**Used in:** Record App (data inserts), Admin (updates)
**Purpose:** Prevent concurrent modification race conditions

### 4. HTML Template Pattern
```javascript
const template = HtmlService.createTemplateFromFile('index');
template.variableName = value;
return template.evaluate()
  .addMetaTag('viewport', 'width=device-width')
  .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
```
**Used in:** All three projects
**Purpose:** Dynamic HTML generation with server-side variables

### 5. Error Handling Pattern
```javascript
try {
  // Main logic
} catch (err) {
  Logger.log('Error: ' + err.message);
  writeLog_([errorMsg], {
    functionName: "functionName",
    status: "Error",
    message: err.message,
    editorName: userName
  });
  throw new Error(userFacingMessage);
}
```
**Used in:** All three projects
**Purpose:** Comprehensive error logging and user feedback

### 6. Webhook Notification Pattern
```javascript
function notifyRecordApp_(updateType) {
  const payload = {
    secret: WEBHOOK_SECRET,
    updateType: updateType
  };
  UrlFetchApp.fetch(RECORD_APP_WEBHOOK_URL, {
    method: 'post',
    payload: JSON.stringify(payload)
  });
}
```
**Used in:** Admin App (notifies Record)
**Purpose:** Trigger cache invalidation across apps

---

## TECHNICAL SUMMARY

### Technology Stack
- **Backend**: Google Apps Script (JavaScript)
- **Frontend**: HTML5, CSS3 (Tailwind-inspired utility classes, Materialize)
- **Database**: Google Sheets (multi-sheet structure)
- **File Storage**: Google Drive (two-stage upload)
- **External APIs**: Google Vision API (OCR), Drive API (resumable upload)
- **Authentication**: HMACSHA256 tokens, email-based 2FA
- **Caching**: Google Apps Script Cache Service

### Deployment
- Three separate Google Apps Script projects
- Each deployed as web app (doGet/doPost endpoints)
- Shared PropertiesService for configuration
- Shared Google Spreadsheet as central data store

### Performance Considerations
- Cache TTL: 1 hour for dropdowns/UI settings, 10 minutes for nonces
- Lock timeout: 10 seconds per operation
- Log retention: 500 most recent entries
- Batch operations: Single POST for multiple items

### Scalability Limits
- Sheets API: ~300 requests/minute per user
- Drive API: ~1 million read requests/day
- Script execution: 6 minute maximum per request
- Concurrent writes: Protected by locks

### Maintenance Points
- Configuration changes require manual Property updates
- Webhook URL changes require both apps' config updates
- TOKEN_SECRET_KEY changes break existing tokens
- Drive folder IDs must be kept current

