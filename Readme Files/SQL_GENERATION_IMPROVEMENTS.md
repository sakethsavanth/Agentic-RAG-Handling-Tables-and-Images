# SQL Generation Improvements for Tables and Images

## Problems Fixed

### 1. **Invalid SQL Functions**
```sql
❌ ERROR: function load_file(unknown) does not exist
LINE 8: ('Cedh Fbh', LOAD_FILE('/path/to/signature_image.png'));
```

### 2. **Special Character Syntax Errors**
```sql
❌ ERROR: syntax error at or near ".2"
LINE 10: (70.6, '–42.2%', –42.2),
          Special dash character (–) causing issues
```

### 3. **Poor Table Naming**
- Tables named generically without document context
- Hard to identify which document/section they came from

### 4. **Missing Data Handling**
- SQL inserts failed when data was missing or unclear

## Solutions Implemented

### ✅ 1. Context-Aware Analysis

**Tables**: Now extract 5 lines before and after each table
```python
# Before
table = extract_table(markdown)

# After  
table = extract_table(markdown, context_lines=5)
# Returns: table_content + context_before + context_after
```

**Images**: Now pass page text context (800 chars)
```python
# Before
analyze_image(image_base64, type="visualization")

# After
analyze_image(image_base64, type="visualization", page_context=page_text)
```

### ✅ 2. Improved SQL Generation Prompts

**Key Instructions Added:**
1. **Table Naming**: Use document context for descriptive names
   ```sql
   -- Before: generic_table
   -- After: wash_mortality_by_region
   ```

2. **Data Types**: 
   - Use `NUMERIC` (not `FLOAT`) for decimals
   - Use `TEXT` for non-numeric data
   - Use `INTEGER` only for whole numbers

3. **Special Characters**:
   - Replace special dashes (–, —) with standard hyphen (-)
   - Escape single quotes properly
   - Remove non-standard Unicode

4. **Missing Data**: Replace with 'NA' (as TEXT)

5. **Forbidden Functions**: DO NOT USE:
   - `LOAD_FILE()`
   - BLOB types
   - File system functions

### ✅ 3. Enhanced Model Selection

Using **Nova Pro** (`us.amazon.nova-pro-v1:0`) for SQL generation:
- Better understanding of complex tables
- More accurate data type inference
- Better context comprehension

## Files Modified

### 1. **`utils/chunking_utils.py`**
```python
# Added context_lines parameter
def extract_tables_from_markdown(markdown_text: str, context_lines: int = 5)
```
- Captures text before/after each table
- Returns `context_before` and `context_after` fields

### 2. **`utils/aws_utils.py`**
```python
# Updated method signatures
def analyze_table(table_text, context_before="", context_after="")
def analyze_image(image_base64, image_type="general", page_context="")
```
- Accepts context parameters
- Improved prompts with explicit instructions
- Better error handling for special characters

### 3. **`agents/document_parse_agent.py`**
- Extracts page text when processing images
- Passes context to both table and image analysis
- Displays context availability in logs

## Expected Results

### Before:
```sql
❌ CREATE TABLE table_1 (
    col1 TEXT,
    col2 FLOAT
);
INSERT INTO table_1 VALUES ('Value', LOAD_FILE(...));
```

### After:
```sql
✅ CREATE TABLE IF NOT EXISTS wash_mortality_regional_data (
    region TEXT,
    mortality_rate NUMERIC,
    change_percentage TEXT
);
INSERT INTO wash_mortality_regional_data VALUES 
    ('African Region', 5.2, '-42.2%'),
    ('European Region', 'NA', '12.5%');
```

## Testing Recommendations

### Test Case 1: Tables with Special Characters
Document with tables containing:
- Special dashes (–, —)
- Percentage symbols
- Missing cells

**Expected**: Clean SQL with standard hyphens and 'NA' for missing data

### Test Case 2: Data Visualizations
Charts/graphs that need data extraction

**Expected**: 
- Descriptive table name from page context
- NUMERIC type for all decimals
- No LOAD_FILE() or file references

### Test Case 3: Complex Tables
Multi-row, multi-column tables with mixed data types

**Expected**:
- Correct data type inference (NUMERIC vs TEXT vs INTEGER)
- All data properly quoted
- Context-based meaningful table name

## Monitoring

Check logs for:
```
✅ Context available: 250 chars before, 180 chars after
✅ Generated SQL CREATE TABLE and INSERT statements
✅ Table created successfully
```

Watch for errors:
```
⚠️ Table creation failed: syntax error...
```
If errors persist, check the generated SQL in the database

 logs.

## Rollback

If issues occur, revert changes to:
- `utils/chunking_utils.py` - Line 184+
- `utils/aws_utils.py` - Lines 152-250
- `agents/document_parse_agent.py` - Lines 260-320, 350-380

## Performance Impact

- **Minimal**: Only adds ~400-800 chars of context text
- **Token increase**: ~100-200 tokens per table/image
- **Quality improvement**: Significant reduction in SQL errors
