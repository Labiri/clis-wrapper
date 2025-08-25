# Chat Mode Refactoring Plan

## Objective
Make chat mode the standard behavior for the Claude Code OpenAI wrapper by removing all raw SDK request logic and simplifying the codebase.

## Current Architecture Analysis

### Dual Mode System
Currently, the system operates in two modes:
1. **Raw SDK Mode** (default without suffix):
   - Full session management with conversation history
   - All Claude tools available
   - No sandboxing
   - Content filtering applied
   
2. **Chat Mode** (activated by `-chat` or `-chat-progress` suffix):
   - No session management
   - Restricted tools (WebSearch, WebFetch, Read for images)
   - Sandboxed execution
   - XML format preservation
   - Progress markers optional with `-chat-progress`

## Refactoring Plan

### Phase 1: Core Removals

#### 1.1 Remove Session Management System
- **Delete files:**
  - `session_manager.py` - Complete session management logic
  - `test_session_simple.py`
  - `test_session_continuity.py` 
  - `test_session_complete.py`
  
- **Remove from `models.py`:**
  - `SessionInfo` class
  - `SessionListResponse` class
  - `session_id` field from `ChatCompletionRequest`

- **Remove from `main.py`:**
  - Session endpoints (`/v1/sessions`, `/v1/sessions/{session_id}`)
  - Session manager initialization in lifespan
  - Session cleanup task

#### 1.2 Keep Session Tracker
- `session_tracker.py` - KEEP (still needed for sandbox cleanup tracking)

### Phase 2: Simplify Request Handling

#### 2.1 Main Endpoint Simplification (`/v1/chat/completions`)

**Current branching to remove:**
```python
# Lines 1852-1862 - Session branching
if is_chat_mode:
    all_messages = request_body.messages
    actual_session_id = None
else:
    all_messages, actual_session_id = session_manager.process_messages(...)

# Lines 1867-1873 - Content filtering
if not is_chat_mode:
    prompt = MessageAdapter.filter_content(prompt)
else:
    logger.debug("Chat mode: Skipping content filtering...")

# Lines 1887-1899 - Tool configuration
if is_chat_mode:
    claude_options['allowed_tools'] = ChatMode.get_allowed_tools()
elif not request_body.enable_tools:
    claude_options['disallowed_tools'] = ALL_CLAUDE_TOOLS
```

**New simplified flow:**
```python
# Always use direct messages (no sessions)
all_messages = request_body.messages

# Never filter content (preserve XML)
# prompt stays unfiltered

# Always use restricted tools
claude_options['allowed_tools'] = ChatMode.get_allowed_tools()
```

### Phase 3: Model and Mode Handling

#### 3.1 Progress Markers Support (IMPORTANT - KEEP)
- **Keep the progress marker suffix logic** (`-progress` suffix)
- Progress markers are orthogonal to chat mode
- Model parsing becomes simpler:
  ```python
  def parse_model_for_progress(model: str) -> Tuple[str, bool]:
      if model.endswith("-progress"):
          return model[:-9], True  # Remove "-progress" suffix
      return model, False
  ```

#### 3.2 Remove Chat Mode Suffix
- Remove `-chat` suffix parsing (no longer needed)
- All requests are chat mode by default

### Phase 4: Streaming Handlers

#### 4.1 Simplify Streaming Functions
- **Keep these functions (for progress markers):**
  - `stream_with_progress_injection()` - For progress markers
  - `stream_final_content_only()` - For non-progress mode
  
- **Simplify `generate_streaming_response()`:**
  - Remove `is_chat_mode` parameter
  - Remove session management code
  - Always use sandbox and restricted tools

### Phase 5: Claude CLI Integration

#### 5.1 Update `claude_cli.py`
- Remove `is_chat_mode` parameter from all methods
- Always apply XML format handling
- Always use sandbox directory
- Simplify `_prepare_prompt_with_injections()` - always inject

### Phase 6: Configuration Updates

#### 6.1 Environment Variables
- **Remove:**
  - `CHAT_MODE` - No longer needed
  - `enable_tools` parameter from models
  
- **Keep:**
  - `SHOW_PROGRESS_MARKERS` - Still controls progress display
  - `CHAT_MODE_CLEANUP_SESSIONS` - Rename to `SANDBOX_CLEANUP_ENABLED`
  - `CHAT_MODE_CLEANUP_DELAY_MINUTES` - Rename to `SANDBOX_CLEANUP_DELAY_MINUTES`

### Phase 7: Tool Configuration

#### 7.1 Tool Restrictions
- Remove `ALL_CLAUDE_TOOLS` constant
- Always use `ChatMode.get_allowed_tools()`
- Special case: Add `Read` tool when images detected

### Phase 8: Test Updates

#### 8.1 Test Modifications
- Delete session-related tests (listed above)
- Update `test_chat_mode.py` → rename to `test_standard_mode.py`
- Update all integration tests to not expect sessions
- Add tests for progress markers working correctly

### Phase 9: Documentation

#### 9.1 Documentation Updates
- **README.md**: Remove session management section
- **API_COMPATIBILITY.md**: Note session endpoints removed
- **SESSION_MANAGEMENT.md**: Delete file
- **DEPLOYMENT.md**: Update configuration section

## Implementation Order

### Stage 1: Model and Configuration Cleanup
1. **Simplify `model_utils.py`**
   - Remove `parse_model_and_mode()` function
   - Create simple `extract_progress_flag(model: str) -> Tuple[str, bool]`
   - Remove all `-chat` suffix handling

2. **Update configuration**
   - Remove `CHAT_MODE` environment variable
   - Rename `CHAT_MODE_CLEANUP_*` to `SANDBOX_CLEANUP_*`
   - Remove `enable_tools` from models.py

### Stage 2: Remove Session System
1. **Delete files completely:**
   - `session_manager.py`
   - `test_session_simple.py`
   - `test_session_continuity.py`
   - `test_session_complete.py`
   - `doc/SESSION_MANAGEMENT.md`

2. **Remove from `main.py`:**
   - All `/v1/sessions` endpoints
   - Session manager import and initialization
   - Session cleanup task in lifespan

3. **Remove from `models.py`:**
   - `SessionInfo` class
   - `SessionListResponse` class
   - `session_id` field from `ChatCompletionRequest`

### Stage 3: Simplify Main Request Handler
1. **In `chat_completions()` function:**
   - Remove all `if is_chat_mode` branches
   - Always use `all_messages = request_body.messages`
   - Never call `session_manager.process_messages()`
   - Always use `ChatMode.get_allowed_tools()`
   - Remove content filtering calls

2. **In streaming functions:**
   - Remove `is_chat_mode` parameter everywhere
   - Simplify `generate_streaming_response()`
   - Keep progress marker logic intact

### Stage 4: Claude CLI Simplification
1. **Update `claude_cli.py`:**
   - Remove `is_chat_mode` parameter from all methods
   - Always use sandbox directory
   - Always apply XML injection logic
   - Simplify `run_completion()` method

### Stage 5: Clean Up Imports and Constants
1. **Remove from `main.py`:**
   - `from session_manager import session_manager`
   - `ALL_CLAUDE_TOOLS` constant
   - Unused model parsing functions

2. **Update all files:**
   - Remove unused imports
   - Clean up type hints

### Stage 6: Update Tests
1. **Create new test structure:**
   - Rename `test_chat_mode.py` to `test_standard_mode.py`
   - Update all tests to not expect sessions
   - Ensure progress markers still work

### Stage 7: Documentation
1. **Update README.md:**
   - Remove session management section
   - Simplify getting started
   - Update examples

2. **Delete obsolete docs:**
   - `SESSION_MANAGEMENT.md`
   - Update `API_COMPATIBILITY.md`

## Benefits

1. **Code Reduction**: ~30% less code to maintain
2. **Simpler Logic**: No branching based on mode
3. **Better Security**: Always sandboxed and restricted
4. **Clearer Purpose**: Optimized for AI assistants
5. **Progress Markers**: Still supported via model suffix

## Migration Guide for Users

### Breaking Changes
1. Session management removed - clients must handle conversation history
2. Model names simplified - no more `-chat` suffix needed
3. Tools always restricted - no `enable_tools` parameter
4. Session endpoints removed - `/v1/sessions/*` no longer exist

### New Behavior
- All requests sandboxed by default
- Tools limited to WebSearch, WebFetch (+ Read for images)
- XML format always preserved
- Progress markers still available with `-progress` suffix

## Design Decisions

1. **No backward compatibility** - Clean break, no legacy support
2. **Remove all `-chat` suffix handling** - Not needed anymore
3. **No session support at all** - Clients handle their own state
4. **Sandbox always enabled** - Non-configurable for security
5. **Gemini models** - Also use sandboxed chat mode by default

## Specific File Changes

### Files to Delete Completely
```
- session_manager.py
- test_session_simple.py
- test_session_continuity.py
- test_session_complete.py
- doc/SESSION_MANAGEMENT.md
- examples/session_continuity.py
- examples/session_curl_example.sh
```

### Major File Modifications

#### `main.py`
- Remove lines: 38 (session_manager import)
- Remove lines: 274 (session_manager.start_cleanup_task)
- Remove lines: 322-323 (session_manager.shutdown)
- Remove lines: 1456-1458 (session processing in streaming)
- Remove lines: 1852-1862 (session branching)
- Remove lines: 1867-1873 (content filtering conditional)
- Remove lines: 1887-1899 (tool configuration branching)
- Remove lines: 1931-1933 (add assistant response to session)
- Remove all `/v1/sessions` endpoints (approximately lines 2000-2100)

#### `claude_cli.py`
- Remove `is_chat_mode` parameter from:
  - `run_completion()` method
  - `_prepare_prompt_with_injections()` method
  - All internal method calls
- Always use sandbox directory creation
- Always apply XML injection logic

#### `models.py`
- Remove `SessionInfo` class
- Remove `SessionListResponse` class
- Remove `session_id: Optional[str]` from `ChatCompletionRequest`
- Remove `enable_tools: bool = False` from `ChatCompletionRequest`

#### `model_utils.py`
- Replace `parse_model_and_mode()` with simple:
  ```python
  def extract_progress_flag(model: str) -> Tuple[str, bool]:
      if model.endswith("-progress"):
          return model[:-9], True
      return model, False
  ```

### Environment Variable Changes
- Remove: `CHAT_MODE`
- Rename: `CHAT_MODE_CLEANUP_SESSIONS` → `SANDBOX_CLEANUP_ENABLED`
- Rename: `CHAT_MODE_CLEANUP_DELAY_MINUTES` → `SANDBOX_CLEANUP_DELAY_MINUTES`

## Detailed Impact Analysis

### Critical Dependencies Found

#### Model Parsing Function Usage
- `parse_model_and_mode()` called in 3 locations:
  - `main.py:1728` - Provider determination
  - `main.py:1755` - Mode and progress parsing  
  - `parameter_validator.py:36` - Model validation
- Returns 3-tuple that must be updated everywhere

#### Session Manager References (14 total in main.py)
- Import: Line 38
- Lifecycle: Lines 274, 323
- Message processing: Lines 673, 1456, 1858
- Response storage: Lines 1009, 1655, 1933
- Session endpoints: Lines 2158-2197

#### Tool Configuration References
- `ALL_CLAUDE_TOOLS` defined: Line 64
- Used for disabling: Lines 705, 1496, 1895
- Must be replaced with `ChatMode.get_allowed_tools()`

### Risk Assessment Matrix

| Component | Risk Level | Impact | Mitigation Strategy |
|-----------|-----------|--------|-------------------|
| Progress Markers | **HIGH** | Breaking streaming | Preserve `-progress` suffix logic completely |
| XML Injection | **MEDIUM** | Response formatting | Test with various prompt types |
| Sandbox Performance | **LOW** | Latency increase | Monitor and optimize cleanup |
| Gemini Compatibility | **MEDIUM** | Provider failure | Test Gemini models thoroughly |
| Missing References | **LOW** | Build errors | Comprehensive grep before deletion |

### Performance Considerations

#### Expected Impacts
- **Positive**: 
  - Removed session management overhead (~10-15% improvement)
  - Simpler request flow (fewer conditionals)
  - Reduced memory usage (no session storage)
  
- **Negative**:
  - All requests use sandbox (I/O overhead ~5-10ms)
  - Cleanup task handles more sessions
  - Potential disk usage increase

#### Monitoring Points
- Request latency (baseline before refactor)
- Memory usage patterns
- Sandbox directory count
- Cleanup task efficiency

### Edge Cases to Handle

1. **XML in Regular Code**: When AI generates XML-like code
   - Current chat mode handles this
   - Test with HTML/XML generation requests

2. **Image Processing**: Special tool enabling for images
   - Keep `ChatMode._check_messages_for_images()`
   - Dynamically add Read tool when needed

3. **Large Responses**: Streaming with progress markers
   - Preserve both streaming modes
   - Test with long-running requests

4. **Concurrent Requests**: Multiple sandboxes
   - Ensure unique sandbox directories
   - Test cleanup under load

### Implementation Checklist

#### Pre-Implementation
- [ ] Create comprehensive test baseline
- [ ] Document current performance metrics
- [ ] Backup current branch
- [ ] Alert team about breaking changes

#### Stage 1: Model and Configuration (Low Risk)
- [ ] Create `extract_progress_flag()` function
- [ ] Update 3 call sites with new tuple structure
- [ ] Test progress marker detection
- [ ] Verify parameter validator works

#### Stage 2: Remove Session System (High Impact)
- [ ] Search for ALL "session" references
- [ ] Delete 7 session-related files
- [ ] Remove 14 references in main.py
- [ ] Remove session endpoints
- [ ] Update OpenAPI schema
- [ ] Verify no dangling imports

#### Stage 3: Simplify Request Handler (Medium Risk)
- [ ] Remove is_chat_mode conditionals (5 locations)
- [ ] Remove ALL_CLAUDE_TOOLS (4 references)
- [ ] Always use ChatMode.get_allowed_tools()
- [ ] Test tool restrictions work

#### Stage 4: Claude CLI Updates (Medium Risk)
- [ ] Remove is_chat_mode parameter (all methods)
- [ ] Always create sandbox directory
- [ ] Simplify XML injection logic
- [ ] Test XML handling edge cases

#### Stage 5: Cleanup and Testing
- [ ] Remove unused imports globally
- [ ] Update all type hints
- [ ] Run mypy for type checking
- [ ] Full test suite execution

#### Stage 6: Documentation
- [ ] Update README.md
- [ ] Delete SESSION_MANAGEMENT.md
- [ ] Update API_COMPATIBILITY.md
- [ ] Create migration guide

### Validation Tests Required

1. **Progress Markers**: 
   - Model with `-progress` suffix shows indicators
   - Model without suffix doesn't show indicators

2. **Tool Restrictions**:
   - WebSearch and WebFetch work
   - File operations blocked
   - Read enabled for images only

3. **Sandbox Isolation**:
   - Each request gets unique sandbox
   - Cleanup happens after delay
   - No file persistence between requests

4. **XML Preservation**:
   - XML tool definitions preserved
   - Response formatting correct
   - No interference with code generation

### Critical Removal Verification (from Gemini insights)

#### Before Deletion - Check for Hidden Dependencies

1. **Session Manager Audit**
   - Check if session_manager stores anything besides conversation history
   - Look for: auth tokens, temp files, user configs
   - If found: These die with sessions (acceptable since no backward compatibility)

2. **Error Message References**
   - Search for error messages mentioning "session"
   - Search for error messages mentioning "enable_tools"
   - Remove all such references

3. **Example Files Using Removed Features**
   ```bash
   grep -r "session_id" examples/
   grep -r "enable_tools" examples/
   grep -r "/v1/sessions" examples/
   ```
   - Delete any examples using these features

4. **Documentation References**
   ```bash
   grep -r "session" *.md doc/*.md
   grep -r "enable_tools" *.md doc/*.md
   grep -r "raw SDK" *.md doc/*.md
   ```
   - Remove all mentions

5. **Unused Dependencies After Removal**
   - Check if any packages were only used by session_manager
   - Remove from pyproject.toml if found

### What We're NOT Doing

❌ **NOT** creating new error handling systems  
❌ **NOT** adding new configuration modules  
❌ **NOT** implementing new testing frameworks  
❌ **NOT** adding performance monitoring  

### What We ARE Doing

✅ **REMOVING** session management completely  
✅ **REMOVING** mode detection logic  
✅ **REMOVING** conditional branches  
✅ **REMOVING** unused tools and constants  
✅ **SIMPLIFYING** to single execution path  

### Rollback Plan

If issues arise:
1. Git revert to backup branch
2. Restore deleted files from git
3. Document what broke

## Next Steps

1. Create feature branch: `git checkout -b refactor/chat-mode-standard`
2. Run baseline tests and performance metrics
3. Execute stages sequentially with validation
4. Monitor each stage for issues
5. Full regression testing
6. Performance comparison
7. Documentation updates
8. Merge to main

## Estimated Timeline

- **Stage 1**: 30 minutes (simple changes)
- **Stage 2**: 1-2 hours (complex removal)
- **Stage 3**: 1 hour (logic simplification)
- **Stage 4**: 1 hour (CLI updates)
- **Stage 5**: 30 minutes (cleanup)
- **Stage 6**: 1 hour (documentation)
- **Testing**: 1-2 hours (comprehensive)

**Total**: 6-8 hours including testing

## Final Verification Summary

### Files Confirmed for Deletion
✅ **Example files using sessions** (found via grep):
- `examples/session_continuity.py` - 40 references to session_id
- `examples/session_curl_example.sh` - 13 references to sessions

✅ **Test files**:
- `test_session_simple.py`
- `test_session_continuity.py`
- `test_session_complete.py`

✅ **Documentation**:
- `doc/SESSION_MANAGEMENT.md`

✅ **Core file**:
- `session_manager.py`

### Code References Found
- **session_manager**: 14 references in main.py
- **is_chat_mode**: 5+ conditional blocks in main.py
- **ALL_CLAUDE_TOOLS**: Defined line 64, used lines 705, 1496, 1895
- **parse_model_and_mode**: Called in 3 locations
- **enable_tools**: In models.py ChatCompletionRequest

### No Additional Features Needed
Per Gemini's feedback, we considered but will NOT implement:
- New error handling systems
- Configuration modules
- Performance monitoring
- Additional testing frameworks

### Pure Removal Focus
This refactoring is strictly about REMOVING complexity:
- Delete 7 files
- Remove 14+ references
- Eliminate 5+ conditional blocks
- Simplify to single execution path

## Parallel Agent Orchestration Strategy

### Why Parallel Execution Works Here
- **Independent file changes**: Most changes don't depend on each other
- **Clear boundaries**: Each agent works on specific files
- **No merge conflicts**: Different files/sections per agent
- **Faster completion**: 3-4 hours vs 6-8 hours sequential

### Phase 1: Independent Deletions (3 Concurrent Agents)
Can run simultaneously with no dependencies:

#### Agent 1: File Deletion Specialist
**Scope**: Delete all session-related files
```
Task: Delete these 7 files completely:
- session_manager.py
- test_session_simple.py  
- test_session_continuity.py
- test_session_complete.py
- examples/session_continuity.py
- examples/session_curl_example.sh
- doc/SESSION_MANAGEMENT.md
```

#### Agent 2: Model Utils Simplification
**Scope**: `model_utils.py`
```
Task: Replace parse_model_and_mode() with:
def extract_progress_flag(model: str) -> Tuple[str, bool]:
    if model.endswith("-progress"):
        return model[:-9], True
    return model, False
Remove all -chat suffix handling.
```

#### Agent 3: Models Cleanup
**Scope**: `models.py`
```
Task: Remove from models.py:
- SessionInfo class
- SessionListResponse class  
- session_id field from ChatCompletionRequest
- enable_tools field from ChatCompletionRequest
```

### Phase 2: Main File Refactoring (3 Concurrent Agents)
After Phase 1 completes:

#### Agent 4: Session References Removal
**Scope**: `main.py` session manager references
```
Task: Remove these 14 session references:
- Line 38: session_manager import
- Line 274: start_cleanup_task()
- Lines 322-323: shutdown()
- Lines 673, 1456, 1858: process_messages()
- Lines 1009, 1655, 1933: add_assistant_response()
- Lines 2158-2197: All /v1/sessions endpoints
```

#### Agent 5: Conditional Logic Removal
**Scope**: `main.py` is_chat_mode branches
```
Task: Simplify these conditionals:
- Lines 1852-1862: Use all_messages = request_body.messages
- Lines 1867-1873: Remove content filtering
- Lines 1887-1899: Use ChatMode.get_allowed_tools()
- Line 64: Remove ALL_CLAUDE_TOOLS constant
- Lines 705, 1496, 1895: Remove ALL_CLAUDE_TOOLS usage
```

#### Agent 6: Import Updates
**Scope**: `parameter_validator.py` and import cleanup
```
Task: Update imports:
- parameter_validator.py line 36: Use extract_progress_flag()
- Remove unused imports globally after deletions
```

### Phase 3: Final Simplifications (2 Concurrent Agents)

#### Agent 7: Claude CLI Cleanup
**Scope**: `claude_cli.py`
```
Task: Remove is_chat_mode parameter:
- From all method signatures
- Always create sandbox
- Always apply XML injection
- Remove mode conditionals
```

#### Agent 8: Documentation Updates
**Scope**: All markdown files
```
Task: Update documentation:
- README.md: Remove session section
- .env.example: Remove CHAT_MODE
- Remove all "raw SDK" references
```

### Orchestration Timeline
```
Hour 0-1: Phase 1 (Agents 1,2,3) - Independent deletions
Hour 1-2.5: Phase 2 (Agents 4,5,6) - Main.py changes
Hour 2.5-3.5: Phase 3 (Agents 7,8) - CLI & docs
Hour 3.5-4: Integration testing & verification
```

### Orchestrator Instructions
```
As orchestrator, you will:
1. Launch agents with specific tasks from each phase
2. Wait for phase completion before starting next
3. Verify no broken references between phases
4. Run quick syntax check after each phase
5. Coordinate final testing
```

### Agent Task Template
```
You are Agent [N] working on chat mode refactoring.
Your task: [SPECIFIC TASK FROM ABOVE]
Constraints:
- Only modify files in your scope
- Do not touch files assigned to other agents
- Report when complete
- If you encounter unexpected dependencies, report back
```

### Conflict Prevention
- Each agent owns specific files
- No overlapping line ranges in main.py
- Clear phase dependencies prevent race conditions
- Orchestrator validates between phases