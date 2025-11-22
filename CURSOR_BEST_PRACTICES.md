# 🎯 Cursor AI Best Practices - Áp dụng cho Baccarat Predictor Pro

> Tổng hợp từ các file hướng dẫn Claude và áp dụng vào dự án hiện tại

---

## 📋 TÓM TẮT CÁC BEST PRACTICES

### 1. Comment-Driven Development ✅

**Nguyên tắc**: Viết comment chi tiết TRƯỚC, để Cursor autocomplete code SAU

**Cấu trúc comment tốt**:
```python
# TEST: [Tên test ngắn gọn]
# Purpose: [Mục đích rõ ràng]
# Input: [Kiểu dữ liệu + ví dụ cụ thể]
# Output: [Kết quả mong đợi + ví dụ]
# Algorithm/Steps:
#   1. [Bước 1 chi tiết]
#   2. [Bước 2 chi tiết]
#   3. [Bước 3 chi tiết]
# Assertions:
#   - [Assert 1]
#   - [Assert 2]
# Edge Cases:
#   - [Edge case 1]
#   - [Edge case 2]

@pytest.mark.asyncio
async def test_name(fixtures):
    # TODO: Cursor - implement theo các bước trên
    pass
```

### 2. Progressive Development ✅

**Chiến lược**: Làm từ dễ → khó, từ đơn giản → phức tạp

**Thứ tự ưu tiên**:
1. ✅ Basic tests (không có dependencies)
2. ✅ Edge case tests (empty data, single item)
3. ✅ Integration tests (nhiều components)
4. ✅ Performance tests (large datasets)

### 3. Template-Based Approach ✅

**Sử dụng templates có sẵn** cho:
- Feature extraction tests
- Pattern analysis tests
- Model training tests
- Prediction tests
- Edge case tests
- Integration tests

### 4. Incremental Testing ✅

**Workflow mỗi test**:
1. Copy template (1 phút)
2. Fill in details (2 phút)
3. Let Cursor autocomplete (1-2 phút)
4. Review & adjust (2-3 phút)
5. Run test (1 phút)
6. Fix if fails (2-5 phút)
7. Commit when passes (1 phút)

**Total**: ~10-15 phút/test

---

## 🎨 ÁP DỤNG VÀO DỰ ÁN BACCARAT PREDICTOR PRO

### A. Khi viết tests mới

#### Template cho Baccarat Engine Tests:

```python
# ============= BACCARAT ENGINE TEST =============

# TEST: [Test function name]
# Purpose: [Mục đích test trong context Baccarat]
# 
# Baccarat Context:
#   - Shoe: [8-deck shoe description]
#   - Cards: [Card tracking details]
#   - Rules: [Baccarat Tableau rules relevant]
#
# Input:
#   - shoe_state: Dict với keys: cards_remaining, running_count, etc.
#   - hand_data: Dict với banker_cards, player_cards
#   Example:
#     shoe_state = {
#         "cards_remaining": 400,
#         "running_count_b": 2.5,
#         "running_count_p": -1.2
#     }
#
# Expected Output:
#   - result: Dict với keys: result, edge, true_count
#   Example:
#     {
#         "result": "B",  # Banker wins
#         "edge_banker": 1.23,
#         "true_count_b": 0.5
#     }
#
# Algorithm:
#   1. [Bước 1 với context Baccarat]
#   2. [Bước 2 với context Baccarat]
#   3. [Bước 3 với context Baccarat]
#
# Assertions:
#   - assert result["result"] in ["B", "P", "T"]
#   - assert isinstance(result["edge_banker"], float)
#   - assert -100 <= result["edge_banker"] <= 100
#
# Edge Cases:
#   - Empty shoe (cards_remaining = 0)
#   - Natural hand (8 or 9 on first 2 cards)
#   - Tie result
#   - Reshuffle needed

@pytest.mark.asyncio
async def test_[function_name](shoe_fixture, hand_fixture):
    # TODO: Cursor - implement Baccarat engine test
    # Follow algorithm steps above
    # Use shoe_fixture and hand_fixture
    pass
```

### B. Khi viết API tests

#### Template cho API v2 Tests:

```python
# ============= API V2 TEST =============

# TEST: [Endpoint] returns [expected result]
# Purpose: Validate [API endpoint] functionality
#
# API Endpoint:
#   POST /api/v2/hands/play
#   GET /api/v2/predictions/predict
#   etc.
#
# Request:
#   Method: [GET/POST/PUT/DELETE]
#   Path: [full path]
#   Body: [request body structure]
#   Example:
#     {
#         "shoe_id": "uuid-string",
#         "result": "B"  # or "P" or "T"
#     }
#
# Expected Response:
#   Status: [200/201/400/404/500]
#   Body: [response structure]
#   Example:
#     {
#         "success": true,
#         "data": {
#             "hand_id": "uuid",
#             "result": "B",
#             "edge": 1.23
#         }
#     }
#
# Test Steps:
#   1. Setup: Create test client và fixtures
#   2. Make request: response = client.post("/api/v2/...", json=data)
#   3. Validate status: assert response.status_code == 200
#   4. Validate structure: assert "data" in response.json()
#   5. Validate values: assert response.json()["data"]["result"] == "B"
#
# Error Cases:
#   - Invalid shoe_id → 404
#   - Missing required field → 422
#   - Invalid result value → 422

@pytest.mark.asyncio
async def test_[endpoint_name](client, test_shoe):
    # TODO: Cursor - implement API test
    # Use FastAPI TestClient
    # Follow test steps above
    pass
```

### C. Khi viết ML tests

#### Template cho ML Model Tests:

```python
# ============= ML MODEL TEST =============

# TEST: [Model component] [behavior]
# Purpose: Validate ML model [specific functionality]
#
# ML Context:
#   - Model: LSTM with attention mechanism
#   - Features: 35+ features (frequency, recency, patterns, etc.)
#   - Target: Predict next game access (game_id)
#
# Training Data:
#   - X: Feature matrix (n_samples, n_features)
#     Features: [frequency, recency, hour, day, popularity, ...]
#   - y: Target labels (game_ids)
#   Example:
#     X = np.array([
#         [10, 0.8, 14, 2, 0.6],  # freq=10, recency=0.8, hour=14, day=Tue, pop=0.6
#         [5, 0.5, 9, 1, 0.3],
#         ...
#     ])
#     y = np.array([5, 3, 5, ...])  # game_ids
#
# Model Pipeline:
#   1. Feature extraction: X = extract_features(logs)
#   2. Feature scaling: X_scaled = scaler.fit_transform(X)
#   3. Model training: model.fit(X_scaled, y)
#   4. Prediction: y_pred = model.predict(X_new)
#
# Expected Results:
#   - Model is trained successfully
#   - Accuracy >= threshold (e.g., 0.7)
#   - Model can predict on new data
#   - Confidence scores are valid [0, 1]
#
# Assertions:
#   - assert model is instance of [ModelType]
#   - assert hasattr(model, 'predict')
#   - assert accuracy >= 0.7
#   - assert all(0 <= conf <= 1 for conf in confidences)

@pytest.mark.asyncio
async def test_[model_component](sample_training_data, model_fixture):
    # TODO: Cursor - implement ML model test
    # Use sample_training_data for X, y
    # Follow model pipeline steps
    pass
```

---

## 🚀 WORKFLOW ĐỀ XUẤT CHO DỰ ÁN

### Daily Workflow

```
Morning (10 phút):
  1. Review progress: git log --oneline
  2. Check test coverage: pytest --cov=app --cov-report=term
  3. Pick next task từ TODO list

Work Session (1-2 giờ):
  4. Open relevant files:
     - Test file cần viết
     - Source file đang test
     - Template file (CURSOR_COMMENT_TEMPLATES.md)
  
  5. Write tests theo workflow:
     - Copy template
     - Fill in Baccarat-specific details
     - Let Cursor autocomplete
     - Run & verify
     - Repeat 3-5 tests

End of Session (10 phút):
  6. Run full test suite: pytest tests/ -v
  7. Check coverage: pytest --cov=app --cov-report=html
  8. Commit: git commit -m "Add tests for [feature]"
  9. Update progress notes
```

### Weekly Review

```markdown
## Week [X] Review

### Tests Completed
- [ ] Feature extraction: X/Y tests
- [ ] Pattern analysis: X/Y tests
- [ ] Model training: X/Y tests
- [ ] Predictions: X/Y tests
- [ ] API endpoints: X/Y tests

### Coverage Progress
- Current: X%
- Target: 85-90%
- Gap: Y%

### Issues & Solutions
1. [Issue]: [Solution]

### Next Week Plan
- Focus: [specific area]
- Target: [milestone]
```

---

## 💡 CURSOR SHORTCUTS & TRICKS

### Essential Shortcuts

| Action | Shortcut | Use When |
|--------|----------|----------|
| Trigger Autocomplete | `Ctrl+Space` | Force suggestion |
| Accept Suggestion | `Tab` | Cursor suggests code |
| Next Suggestion | `Alt+]` | Cycle through options |
| Previous Suggestion | `Alt+[` | Go back |
| Dismiss | `Esc` | Reject suggestion |

### Cursor Triggers cho Baccarat Project

```python
# Pattern 1: TODO với context
# TODO: Cursor - implement Baccarat hand playing logic
# Context: 8-deck shoe, Tableau rules, card counting
pass

# Pattern 2: Detailed với examples
# Play a Baccarat hand
# Input: shoe_state = {"cards_remaining": 400, "running_count_b": 2.5}
# Output: {"result": "B", "edge": 1.23, "true_count": 0.5}
# Steps:
#   1. Deal initial 2 cards to Banker and Player
#   2. Check for naturals (8 or 9)
#   3. Apply Tableau rules for third card
#   4. Calculate winner
#   5. Update card counts
pass

# Pattern 3: Type hints
async def play_hand(shoe_state: Dict[str, Any]) -> Dict[str, Any]:
    # TODO: Cursor - implement
    pass
```

---

## 🐛 DEBUGGING STRATEGY

### Khi test fails

```bash
# 1. Show full error
pytest tests/test_file.py::test_name -vv

# 2. Show local variables
pytest tests/test_file.py::test_name -v -l

# 3. Drop vào debugger
pytest tests/test_file.py::test_name -v --pdb

# 4. Show print statements
pytest tests/test_file.py::test_name -v -s

# 5. Full traceback
pytest tests/test_file.py::test_name -v --tb=long
```

### Common Issues trong Baccarat Project

| Issue | Solution |
|-------|----------|
| Import Error | Check `sys.path`, add `__init__.py` |
| Async Error | Ensure `@pytest.mark.asyncio` |
| Mock Not Working | Use `AsyncMock()` for async functions |
| Shoe State Error | Verify shoe fixture setup |
| Card Counting Error | Check EOR values calculation |

---

## 📊 PROGRESS TRACKING

### Test Coverage Goals

| Phase | Tests | Coverage | Status |
|-------|-------|----------|--------|
| Foundation | Core engine tests | 40-50% | ✅ |
| API Tests | API v2 endpoints | 55-65% | ✅ |
| ML Tests | Model training & prediction | 70-75% | ✅ |
| Integration | End-to-end tests | 85-90% | ⏳ |

### Commands để track

```bash
# Check coverage
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# Run specific test file
pytest tests/test_engine.py -v

# Run tests by keyword
pytest tests/ -k "prediction" -v

# Run failed tests only
pytest --lf -v
```

---

## ✅ CHECKLIST CHO MỖI TEST

### Before Writing
- [ ] Đã đọc source code cần test
- [ ] Hiểu business logic
- [ ] Chọn template phù hợp
- [ ] Có examples cụ thể

### While Writing
- [ ] Comment chi tiết với examples
- [ ] Có type hints
- [ ] Có edge cases
- [ ] Có assertions rõ ràng

### After Writing
- [ ] Test passes
- [ ] Code coverage tăng
- [ ] No warnings
- [ ] Committed to git

---

## 🎯 ÁP DỤNG NGAY

### Next Steps

1. **Review existing tests** để hiểu pattern
2. **Pick một feature** cần test thêm
3. **Copy template** phù hợp
4. **Fill in Baccarat-specific details**
5. **Let Cursor help** implement
6. **Run & verify**

### Files để reference

- `backend/tests/test_engine.py` - Engine tests examples
- `backend/tests/test_api_v2.py` - API tests examples
- `backend/tests/test_predictions.py` - ML tests examples
- `CURSOR_COMMENT_TEMPLATES.md` - Templates (nếu có)

---

## 📚 RESOURCES

### Internal
- Test files trong `backend/tests/`
- Source code trong `backend/app/`
- Documentation trong `docs/`

### External
- Pytest docs: https://docs.pytest.org/
- Cursor docs: https://cursor.sh/docs
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/

---

**Remember**: 
- ✅ Comment chi tiết = Cursor hiểu tốt hơn
- ✅ Examples cụ thể = Code chính xác hơn
- ✅ Test thường xuyên = Phát hiện lỗi sớm
- ✅ Commit thường xuyên = Dễ rollback

**Happy Coding với Cursor AI! 🚀**

