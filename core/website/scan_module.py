# from django.http import HttpResponseRedirect
# from django.shortcuts import get_object_or_404, redirect
# from django.http import HttpResponse
# from .models import Photo
import os
import json
import pandas as pd
import json
import io
import csv
import re
from openpyxl import load_workbook
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.shared import Pt, Cm
from pathlib import Path
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_TAB_ALIGNMENT, WD_TAB_LEADER

def load_keywords_from_json():
    """
    Load keywords from a JSON file relative to the current script.

    Returns:
    - dict: The loaded keyword dictionary from the JSON file.
    """
    # Determine the directory of this script (where this code is running)
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Construct the relative path to the JSON file (assuming it's in core/website/keywords.json)
    json_file = os.path.join(current_directory, 'keywords.json')

    try:
        # Open and load the JSON file with UTF-8 encoding
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {json_file}")

    return data

# a =load_keywords_from_json()
# print(a)


def extract_and_iterate_docx_content(file_path, table_id=None, **pandas_kwargs):
    """
    Extracts all content from a DOCX file, including headers, footers, paragraphs, and tables.


    Parameters:
    - file_path: Path to the DOCX file.
    - table_id: (Optional) Index of the specific table to extract. If None, all tables will be extracted.
    - pandas_kwargs: Optional keyword arguments passed to `pd.read_csv()` for parsing tables.


    Returns:
    - list: List of extracted content (paragraphs, tables, headers) as lowercase strings.
    """
    document = Document(file_path)
    content_list = []

    def extract_single_table(table):
        """
        Extract content from a single table and return it as a pandas DataFrame.


        Parameters:
        - table: The table object from the DOCX document.


        Returns:
        - pd.DataFrame: Table content converted into a DataFrame.
        """
        memory_file = io.StringIO()
        csv_writer = csv.writer(memory_file)

        # Extract each row from the table and write to the memory buffer
        for row in table.rows:
            csv_writer.writerow([cell.text.strip() for cell in row.cells])

        memory_file.seek(0)
        return pd.read_csv(memory_file, **pandas_kwargs)

    # Extract paragraphs and tables from the body
    for child_element in document.element.body.iterchildren():
        if isinstance(child_element, CT_P):
            # Extract and clean paragraph text, then convert to lowercase
            paragraph = Paragraph(child_element, document).text.strip().lower()
            if paragraph:  # Only append non-empty paragraphs
                content_list.append(paragraph)
        elif isinstance(child_element, CT_Tbl):
            table = Table(child_element, document)
            if table_id is None or document.tables.index(table) == table_id:
                # Convert the table to string before adding to the content_list
                table_df = extract_single_table(table)
                content_list.append(table_df.to_string(index=False).lower())

    # Extract headers and footers
    for section in document.sections:
        # Extract headers
        for header in section.header.paragraphs:
            header_text = header.text.strip().lower()
            if header_text:
                content_list.append(header_text)

    return content_list


def find_keywords_and_patterns_in_docx(content_list, keywords_dict, patterns):
    """
    Search for both keywords and regex patterns in DOCX content, and return the count of occurrences.


    Parameters:
    - content_list: List of content extracted from the DOCX file.
    - keywords_dict: Dictionary of keywords to search for.
    - patterns: Dictionary of regex patterns to search for.


    Returns:
    - str: JSON formatted string containing the search results for keywords and patterns.
    """
    found_keywords = []
    found_patterns = []
    keyword_counts = {}  # Initialize keyword counts
    pattern_counts = {}  # Initialize pattern counts

    # Convert DOCX content into a single lowercase string
    docx_content_lower = " ".join(
        [str(content).strip().lower() for content in content_list])

    # Search for keywords
    for keyword_list in keywords_dict.values():
        for keyword in keyword_list:
            # Convert keyword to lowercase and strip whitespace
            keyword_lower = keyword.lower().strip()
            keyword_counts[keyword_lower] = 0  # Initialize count

            # Count occurrences of the keyword in the DOCX content
            keyword_counts[keyword_lower] += docx_content_lower.count(
                keyword_lower)

            # If keyword is found, add it to the result
            if keyword_counts[keyword_lower] > 0:
                found_keywords.append({
                    "Found Keyword": keyword,
                    "num of the same keyword": keyword_counts[keyword_lower]
                })

    # Search for regex patterns
    for pattern_name, pattern_regex in patterns.items():
        pattern_counts[pattern_name] = 0  # Initialize count

        # Find all matches for the pattern in the DOCX content
        matches = pattern_regex.findall(docx_content_lower)
        pattern_counts[pattern_name] += len(matches)  # Increment pattern count

        # If pattern is found, add it to the result
        if pattern_counts[pattern_name] > 0:
            found_patterns.append({
                "Pattern Name": pattern_name,
                "num of the same pattern": pattern_counts[pattern_name]
            })

    # Combine the results into a dictionary
    result = {
        "Keywords": found_keywords,
        "Patterns": found_patterns
    }

    # Convert the result to a JSON string and return it
    json_result = json.dumps(result, indent=4, ensure_ascii=False)
    return json_result


# Main function to check keywords and patterns in a DOCX file
def check_keywords_and_patterns_in_docx(file_path, patterns):
    """
    Check the DOCX content for both keywords and regex patterns.


    Parameters:
    - file_path: Path to the DOCX file.
    - patterns: Dictionary of regex patterns to search for.


    Returns:
    - str: JSON formatted string containing the search results.
    """
    # Load keywords from JSON file
    keywords_dict = load_keywords_from_json()

    # Extract content from DOCX
    content_list = extract_and_iterate_docx_content(file_path)

    # Find both keywords and patterns
    result = find_keywords_and_patterns_in_docx(
        content_list, keywords_dict, patterns
    )

    return result


def extract_and_iterate_excel_content(file_path, **pandas_kwargs):
    """
    Extract content from all sheets of an Excel file, including column headers.


    Parameters:
    - file_path: Path to the Excel file.
    - pandas_kwargs: Optional keyword arguments passed to `pd.read_excel()`.


    Returns:
    - dict: Dictionary where each sheet name maps to a list of extracted content.
    """
    # Read all sheets as dataframes, ensuring all data is read as strings
    sheet_dict = pd.read_excel(
        file_path, sheet_name=None, dtype=str, **pandas_kwargs
    )

    content_dict = {}

    for sheet_name, df in sheet_dict.items():
        content_list = []

        # Add column names, ignoring 'Unnamed' columns
        headers = df.columns
        content_list.extend([str(header).strip()
                             for header in headers if "Unnamed" not in header])

        # Add each cell content to the list, ignoring 'Unnamed' cells
        for _, row in df.iterrows():
            for cell in row:
                cell_str = str(cell).strip()
                if pd.notnull(cell) and "Unnamed" not in cell_str:
                    content_list.append(cell_str)

        content_dict[sheet_name] = content_list

    return content_dict


def find_keywords_and_patterns_in_excel(excel_content_dict, keywords_dict, patterns):
    """
    Search for both keywords and regex patterns in Excel content.


    Parameters:
    - excel_content_dict: Dictionary of content from Excel sheets.
    - keywords_dict: Dictionary of keywords to search for.
    - patterns: Dictionary of regex patterns to search for.


    Returns:
    - str: JSON formatted string containing search results.
    """
    found_keywords = []
    found_patterns = []

    for sheet_name, excel_content in excel_content_dict.items():
        keyword_counts = {}
        pattern_counts = {}

        # Search for keywords
        for keyword_list in keywords_dict.values():
            for keyword in keyword_list:
                keyword_lower = keyword.lower().strip()  # Normalize keyword
                keyword_counts[keyword_lower] = 0  # Initialize count

                # Count occurrences of each keyword in the sheet content
                for content in excel_content:
                    content_clean = str(content).strip().lower()
                    keyword_counts[keyword_lower] += content_clean.count(
                        keyword_lower)

                # If keyword is found, save the result
                if keyword_counts[keyword_lower] > 0:
                    found_keywords.append({
                        "Sheet": sheet_name,
                        "Found Keyword": keyword,
                        "num of the same keyword": keyword_counts[keyword_lower]
                    })

        # Search for regex patterns
        for pattern_name, pattern_regex in patterns.items():
            pattern_counts[pattern_name] = 0  # Initialize count

            # Search for patterns in the sheet content
            for content in excel_content:
                matches = pattern_regex.findall(content)
                pattern_counts[pattern_name] += len(matches)

            # If pattern is found, save the result
            if pattern_counts[pattern_name] > 0:
                found_patterns.append({
                    "Sheet": sheet_name,
                    "Pattern Name": pattern_name,
                    "num of the same pattern": pattern_counts[pattern_name]
                })

    # Combine results into a dictionary
    result = {
        "Keywords": found_keywords,
        "Patterns": found_patterns
    }

    # Convert result to JSON and return
    json_result = json.dumps(result, indent=4, ensure_ascii=False)
    return json_result


# Main function to check keywords and patterns in an Excel file
def check_keywords_and_patterns_in_excel(xlsx_file, patterns):
    """
    Check an Excel file for both keywords and regex patterns.


    Parameters:
    - xlsx_file: Path to the Excel file.
    - patterns: Dictionary of regex patterns to search for.


    Returns:
    - str: JSON formatted string containing search results.
    """
    # Load keywords from JSON file
    keywords_dict = load_keywords_from_json()

    # Extract content from Excel file
    excel_content_dict = extract_and_iterate_excel_content(xlsx_file)

    # Find both keywords and patterns in the Excel content
    result = find_keywords_and_patterns_in_excel(
        excel_content_dict, keywords_dict, patterns
    )

    return result


def define_rules():
    """
    Define a set of rules consisting of various keywords to search for.


    Returns:
    - dict: Dictionary of rule sets where each rule contains relevant keywords.
    """
    rules = {
        "rule_1": {
            "email": "email",
            "id number (cccd/cmnd)": "id number (cccd/cmnd)",
            "tên khách hàng": [
                "tên khách hàng", "họ tên", "họ và tên", "họ tên", "name", "full name"
            ],
            "địa chỉ": "địa chỉ",
            "số điện thoại": "số điện thoại"
        },
        "rule_2": {
            "số thẻ": "số thẻ",
            "cvv": "cvv",
            "ngày hết hạn": "ngày hết hạn",
            "tên chủ thẻ": [
                "tên khách hàng", "chủ thẻ", "tên chủ thẻ", "họ và tên", "họ tên", "name", "full name"
            ]
        },
        "rule_3": {
            "thông tin về chủ trương đầu tư dự án cntt (thời điểm phát hành hồ sơ mời thầu)": 
                [
                    "dự án", "mục tiêu đầu tư", "sự cần thiết", "phương án đầu tư", "hạng mục", "cấu phần mua sắm", 
                    "tuân thủ kiến trúc", "phương án kỹ thuật sơ bộ", "khai toán", "hiệu quả đầu tư", "báo giá"
                ],
            "thông tin về tiêu chuẩn kinh tế kỹ thuật của dự án cntt (trước thời điểm phát hành hồ sơ mời thầu)": 
                [
                    "kinh tế kỹ thuật", "căn cứ pháp lý", "nội dung dự án", "mục tiêu đầu tư", "tổng mức đầu tư", 
                    "mức độ tuân thủ kiến trúc", "yêu cầu về làm chủ", "hình thức mua sắm bản quyền", 
                    "cấp độ hệ thống thông tin", "mức độ kiểm soát", "rủi ro", "tiêu chuẩn kỹ thuật", 
                    "dự toán chi tiết", "kế hoạch lựa chọn nhà thầu", "giá gói thầu", "phương thức lựa chọn nhà thầu"
                ],
            "thông tin mời thầu của dự án cntt (trước thời điểm phát hành hồ sơ mời thầu)": 
                [
                    "hồ sơ mời thầu", "số hiệu gói thầu", "tên gói thầu", "thủ tục đấu thầu", 
                    "yêu cầu về kỹ thuật", "biểu mẫu hợp đồng", "chỉ dẫn nhà thầu", 
                    "bảng dữ liệu đầu thầu", "biểu mẫu mời thầu và dự thầu", 
                    "tiêu chuẩn đánh giá về kỹ thuật", "năng lực và kinh nghiệm"
                ]
        },
        "rule_4": [
            "dntd bq", "dntd ck", "hđv bq", "hđv ck", "tnt", "nim td", "nim hđv", 
            "số lượng kh", "số lượng khách hàng", "slkh", "số lượng sản phẩm", "slsp", "cir", "cltc"
        ],
        "rule_5": [
            "etl", "tài liệu mapping chi tiết"
        ]
    }


    return rules


def scan_file(file_path):
    """
    Scan a file and check for both keywords and patterns depending on the file type.


    Parameters:
    - file_path: Path to the file to be scanned.


    Returns:
    - dict: JSON object with the scan results.
    - str: Error or success message.
    """
    if not file_path:
        return None, "Vui lòng chọn một file trước khi scan."

    file_extension = Path(file_path).suffix.lower()

    # Define patterns (include all necessary patterns)
    patterns = {
        "stk 10 số chứa 3 BDS": re.compile(
            r'\b(111|116|117|118|119|120|121|122|123|124|125|126|128|'
            r'129|130|131|132|133|134|135|136|138|139|140|141|144|'
            r'145|147|149|150|151|159|160|166|168|169|177|180|181|'
            r'186|188|189|199|211|212|213|214|215|216|217|220|222|'
            r'256|260|261|268|279|289|310|311|313|314|315|317|318|'
            r'319|321|328|330|341|345|351|362|368|371|375|376|390|'
            r'395|398|411|421|425|426|427|428|431|432|433|440|441|'
            r'443|444|448|450|451|452|455|460|461|465|466|468|471|'
            r'480|482|483|486|488|501|502|505|512|513|518|520|522|'
            r'531|532|540|556|558|560|561|562|566|565|570|573|580|'
            r'581|590|601|602|611|615|620|621|625|631|632|633|635|'
            r'636|641|642|646|650|651|652|653|655|656|661|670|671|'
            r'672|679|680|686|691|696|701|702|710|711|721|729|730|'
            r'735|737|741|742|745|748|750|753|760|761|762|766|780|'
            r'785|788)\d{7}\b'),
        "cvv": re.compile(r"(?i)(\bCVV\b[\s\S]*?\b\d{3}\b)"),
        "id number (cccd/cmnd)": re.compile(
            r'\b(?:cmnd|cccd|CMND|CCCD)\b.*\b\d{9}\b|\b(?:cmnd|cccd|CMND|CCCD)\b.*\b\d{12}\b|\b\d{9}\b|\b\d{12}\b'),
        "địa chỉ": re.compile(r'(\d+)\s+(đường|phố|phường|quận|thành phố)\s+(\w+),\s+(\w+),\s+(\w+)'),
        "giá trị tiền tối thiểu 6 chữ số": re.compile(r'\b\d{1,3}(,\d{3}){1,}\b'),
        "số điện thoại": re.compile(r'\b(0\d{9}|\+[\d]{11})\b'),
        "email": re.compile(r'\S+@\S+'),
        "số thẻ": re.compile(
            r'''
            \b                                        # Start of word boundary
            (?:9704|476632|411153|428695|427126|402460|406220|511957|
            517107|517453|542726|530515|515110|51511)  # Card prefixes
            (                                         # Matching options
                \d{10,15}                             # 10-15 digit numbers
                |\d{16}                               # 16 digit numbers
                |\d{19}                               # 19 digit numbers
                |\d{20}                               # 20 digit numbers
                |\d{3} \d{4} \d{4} \d{4} \d{4}        # 16 digits in 3-4-4-4 groups
                |\d{4} \d{4} \d{4} \d{4} \d{3}        # 19 digits in 4-4-4-4-3 groups
                |\d{4} \d{4} \d{4} \d{4} \d{4}        # 20 digits in 4-4-4-4-4 groups
            )
            \b                                        # End of word boundary
            ''', re.VERBOSE),
        "số tài khoản ẩn": re.compile(
            r'\b(?:9704|476632|411153|428695|427126|402460|406220|511957|517107|517453|542726|530515|515110)(?:\d{2}xxxx\d{4}|\d{3}xxxx\d{4}|\d{4}xxxx\d{4})\b')
    }

    # Initialize the results variable
    results = None

    # Check the file type and process accordingly
    if file_extension == '.docx':
        results = check_keywords_and_patterns_in_docx(file_path, patterns)
    elif file_extension == '.xlsx':
        results = check_keywords_and_patterns_in_excel(file_path, patterns)
    elif file_extension in [".pdf", ".ptpx", "tsv", "txt", "py", "png", "jpg"]:
        results = "chưa làm"  # Not yet implemented for these types

    # Return error if no results are found
    if results is None:
        return None, "Không có kết quả hợp lệ từ file đã chọn."

    results_json = json.loads(results)
    e1 = "for testing: code đang ở đây"
    print("x"*30, e1)
    print(results_json)
    print(type(results_json)) # nó là dict
    return results_json
 
# Kết quả trả về của results_json mẫu dưới đây
# {
#   "Keywords": [
#     {
#       "Found Keyword": "chủ thẻ",
#       "num of the same keyword": 1
#     },
#     {
#       "Found Keyword": "Dự án",
#       "num of the same keyword": 1
#     },
#     {
#       "Found Keyword": "Mục tiêu đầu tư",
#       "num of the same keyword": 1
#     },
#     {
#       "Found Keyword": "Sự cần thiết",
#       "num of the same keyword": 1
#     },
#     {
#       "Found Keyword": "Phương án đầu tư",
#       "num of the same keyword": 1
#     }
#   ],
#   "Patterns": [
#     {
#       "Pattern Name": "số điện thoại",
#       "num of the same pattern": 1
#     },
#     {
#       "Pattern Name": "email",
#       "num of the same pattern": 1
#     }
#   ]
# }




def convert_string_to_json_rule_one(input_string):
    """
    Convert an input string to JSON format based on matched keywords and pattern counts for rule 1.


    Parameters:
    - input_string: Input string to be converted.


    Returns:
    - str: Pretty-printed JSON string.
    """
    matched_part = input_string.split(
        "matched: ")[1].split(". Pattern counts: ")[0]
    patterns_part = input_string.split("Pattern counts: ")[1]

    # Convert matched keys to a list
    matched_keys = matched_part.split(", ")

    # Convert pattern counts to a dictionary
    pattern_counts = {}
    for pattern in patterns_part.split(", "):
        key, value = pattern.split(": ")
        pattern_counts[key.strip()] = int(value.strip())

    result_json = {
        "rule": 1,
        "matched_keys": matched_keys,
        "pattern_counts": pattern_counts
    }

    pretty_json = json.dumps(result_json, indent=4, ensure_ascii=False)
    return pretty_json


def convert_string_to_json_rule_two(input_string):
    """
    Convert an input string to JSON format based on matched keywords for rule 2.


    Parameters:
    - input_string: Input string to be converted.


    Returns:
    - str: Pretty-printed JSON string.
    """
    rule_part = input_string.split("rule ")[1].split(":")[0]
    matched_part = input_string.split(": ")[1]

    # Convert matched keys to a list
    matched_keys = matched_part.split(", ")

    result_json = {
        "rule": int(rule_part),  # Convert rule to integer
        "matched_keys": matched_keys
    }

    pretty_json = json.dumps(result_json, indent=4, ensure_ascii=False)
    return pretty_json



# def classify_document_with_multiple_rules(results, rules):
#     """
#     Classify a document based on multiple rules by checking keywords and patterns.


#     Parameters:
#     - results: Dictionary containing scan results with found keywords and patterns. Here, result = result_json in scan_file func.
#     - rules: Dictionary containing multiple rule sets to compare with results.


#     Returns:
#     - str: Classification label (e.g., 'Confidential', 'Public', etc.).
#     - str: JSON string with classification details or an error message.
#     """
#     if results == "chưa làm" or results is None:
#         return "chưa làm", "Hiện tại không hỗ trợ định dạng tệp."

#     if not isinstance(results, dict):
#         return "Unsupport file", "Kết quả không hợp lệ."

#     if 'Keywords' not in results or not isinstance(results['Keywords'], list):
#         return "Public", "Không tìm thấy từ khóa hợp lệ trong kết quả."

#     try:
#         # Extract keywords and patterns from the results
#         found_keywords = {item['Found Keyword'] for item in results['Keywords'] if isinstance(
#             item, dict) and 'Found Keyword' in item}
#         found_patterns = {item['Pattern Name']: item['num of the same pattern']
#                           for item in results['Patterns'] if isinstance(item, dict) and 'Pattern Name' in item and 'num of the same pattern' in item}
#     except TypeError as e:
#         return "Internal", f"Đã xảy ra lỗi khi phân tích kết quả: {str(e)}"

#     def matches_keywords_rule(result_keywords, rule_keywords):
#         """
#         Helper function to check if any keywords from the result match the rule's keywords.
#         """
#         if isinstance(rule_keywords, list):
#             return any(keyword in result_keywords for keyword in rule_keywords)
#         return rule_keywords in result_keywords

#     # Condition For Rule 1: Match at least 3 values and check if certain patterns have count >= 10
#     rule_1_matches = 0
#     matched_rule_1_keys = []
#     matched_pattern_counts = []

#     for key, value in rules['rule_1'].items():
#         keyword_match = matches_keywords_rule(found_keywords, value)
#         pattern_match = key in found_patterns and found_patterns[key] >= 10

#         if keyword_match or pattern_match:
#             rule_1_matches += 1
#             matched_rule_1_keys.append(key)
#             if pattern_match:
#                 matched_pattern_counts.append(f"{key}: {found_patterns[key]}")

#     # if rule_1_matches >= 3:
#     #     sms_scan = f"Tìm thấy nội dung mật rule 1: {rule_1_matches} key(s) matched: {', '.join(matched_rule_1_keys)}. Pattern counts: {', '.join(matched_pattern_counts)}"
#     #     pretty_sms_scan = convert_string_to_json_rule_one(sms_scan)
#     #     return "Confidential", pretty_sms_scan
    
#     if rule_1_matches >= 3:
#     # Tạo JSON trực tiếp
#         result_json = {
#             "rule": 1,
#             "matched_keys": matched_rule_1_keys,  # Giả sử đây là danh sách các từ khóa khớp
#             "pattern_counts": matched_pattern_counts  # Giả sử đây là dictionary chứa thông tin pattern counts
#         }
#         # Trả về JSON định dạng chuẩn và đẹp
#         pretty_sms_scan = json.dumps(result_json, indent=4, ensure_ascii=False)
#         return "Confidential", pretty_sms_scan

#     # Condition For Rule 2: All keys in rule_2 must match
#     rule_2_matches = True
#     matched_rule_2_keys = []

#     for key, value in rules['rule_2'].items():
#         keyword_match = matches_keywords_rule(found_keywords, value)
#         pattern_match = key in found_patterns

#         if not (keyword_match or pattern_match):
#             rule_2_matches = False
#             break
#         matched_rule_2_keys.append(key)

#     # if rule_2_matches:
#     #     sms_scan = f"Tìm thấy nội dung mật trong rule 2: {', '.join(matched_rule_2_keys)}"
#     #     pretty_sms_scan = convert_string_to_json_rule_two(sms_scan)
#     #     return "Confidential", pretty_sms_scan
#     if rule_2_matches:
#         # Tạo JSON trực tiếp
#         result_json = {
#             "rule": 2,
#             "matched_keys": matched_rule_2_keys  # Giả sử matched_rule_2_keys là danh sách các từ khóa khớp
#         }
#         # Trả về JSON định dạng chuẩn và đẹp
#         pretty_sms_scan = json.dumps(result_json, indent=4, ensure_ascii=False)
#         return "Confidential", pretty_sms_scan


#     # Check matches for rules 3, 4, and 5
#     matched_rule = None
#     matched_keywords = set()

#     for rule_id, rule_keywords in rules.items():
#         if rule_id in ["rule_3", "rule_4", "rule_5"]:
#             if isinstance(rule_keywords, dict):  # Rule is a dict of keyword lists
#                 for subkey, sub_keywords in rule_keywords.items():
#                     if matches_keywords_rule(found_keywords, sub_keywords):
#                         matched_rule = int(rule_id.split("_")[1])
#                         matched_keywords.update(
#                             keyword for keyword in found_keywords if keyword in sub_keywords)
#             elif isinstance(rule_keywords, list):  # Rule is a flat list of keywords
#                 if matches_keywords_rule(found_keywords, rule_keywords):
#                     matched_rule = int(rule_id.split("_")[1])
#                     matched_keywords.update(
#                         keyword for keyword in found_keywords if keyword in rule_keywords)

#     # If matches found for rule 3, 4, or 5, return the classified label and details
#     if matched_rule:
#         sms = {
#             "rule": matched_rule,
#             "matched_keys": list(matched_keywords)
#         }
#         pretty_sms = json.dumps(sms, indent=4, ensure_ascii=False)

#         return "Confidential", pretty_sms

#     # If no conditions match, return "Internal"
#     return "Internal", "Không tìm thấy nội dung mật"



def classify_document_with_multiple_rules(results, rules):
    """
    Classify a document based on multiple rules by checking keywords and patterns.

    Parameters:
    - results: Dictionary containing scan results with found keywords and patterns. 
               Here, result = result_json in scan_file func.
    - rules: Dictionary containing multiple rule sets to compare with results.

    Returns:
    - str: Classification label (e.g., 'Confidential', 'Public', etc.).
    - str: JSON string with classification details or an error message.
    """
    if results == "chưa làm" or results is None:
        return "chưa làm", "Hiện tại không hỗ trợ định dạng tệp."

    if not isinstance(results, dict):
        return "Unsupport file", "Kết quả không hợp lệ."

    if 'Keywords' not in results or not isinstance(results['Keywords'], list):
        return "Public", "Không tìm thấy từ khóa hợp lệ trong kết quả."

    try:
        # Extract keywords and patterns from the results
        found_keywords = {item['Found Keyword'] for item in results['Keywords'] if isinstance(
            item, dict) and 'Found Keyword' in item}
        found_patterns = {item['Pattern Name']: item['num of the same pattern']
                          for item in results['Patterns'] if isinstance(item, dict) and 'Pattern Name' in item and 'num of the same pattern' in item}
    except TypeError as e:
        return "Internal", f"Đã xảy ra lỗi khi phân tích kết quả: {str(e)}"

    def matches_keywords_rule(result_keywords, rule_keywords):
        """
        Helper function to check if any keywords from the result match the rule's keywords.
        """
        if isinstance(rule_keywords, list):
            return any(keyword in result_keywords for keyword in rule_keywords)
        return rule_keywords in result_keywords

    # Initialize the list to collect satisfied rules
    satisfied_rules = []

    # Check Rule 1
    rule_1_matches = 0
    matched_rule_1_keys = []
    matched_pattern_counts = []

    for key, value in rules['rule_1'].items():
        keyword_match = matches_keywords_rule(found_keywords, value)
        pattern_match = key in found_patterns and found_patterns[key] >= 10

        if keyword_match or pattern_match:
            rule_1_matches += 1
            matched_rule_1_keys.append(key)
            if pattern_match:
                matched_pattern_counts.append(f"{key}: {found_patterns[key]}")

    if rule_1_matches >= 3:
        satisfied_rules.append({
            "rule": 1,
            "matched_keys": matched_rule_1_keys,
            "pattern_counts": matched_pattern_counts
        })

    # Check Rule 2
    rule_2_matches = True
    matched_rule_2_keys = []

    for key, value in rules['rule_2'].items():
        keyword_match = matches_keywords_rule(found_keywords, value)
        pattern_match = key in found_patterns

        if not (keyword_match or pattern_match):
            rule_2_matches = False
            break
        matched_rule_2_keys.append(key)

    if rule_2_matches:
        satisfied_rules.append({
            "rule": 2,
            "matched_keys": matched_rule_2_keys
        })

    # Check Rules 3, 4, 5
    for rule_id, rule_keywords in rules.items():
        if rule_id in ["rule_3", "rule_4", "rule_5"]:
            matched_keywords = set()
            if isinstance(rule_keywords, dict):  # Rule is a dict of keyword lists
                for subkey, sub_keywords in rule_keywords.items():
                    if matches_keywords_rule(found_keywords, sub_keywords):
                        matched_keywords.update(
                            keyword for keyword in found_keywords if keyword in sub_keywords)
            elif isinstance(rule_keywords, list):  # Rule is a flat list of keywords
                if matches_keywords_rule(found_keywords, rule_keywords):
                    matched_keywords.update(
                        keyword for keyword in found_keywords if keyword in rule_keywords)

            if matched_keywords:
                satisfied_rules.append({
                    "rule": int(rule_id.split("_")[1]),
                    "matched_keys": list(matched_keywords)
                })

    # Return all satisfied rules if any
    if satisfied_rules:
        pretty_sms_scan = json.dumps(satisfied_rules, indent=4, ensure_ascii=False)
        return "Confidential", pretty_sms_scan

    # Default case: No matches for any rules
    return "Public", "Không có quy tắc nào được áp dụng."


def label_docx_file(file_path, classify):
    """
    Add or overwrite a label in the footer of a DOCX file based on the scan results.


    Parameters:
    - file_path: Path to the DOCX file.
    - classify: Classification of the document ('Confidential', 'Internal', etc.).


    Returns:
    - str: Label text applied to the document.
    """
    # Load the DOCX document
    document = Document(file_path)

    # Scan the file to classify it
    scan_result = scan_file(file_path)
    rul = define_rules()
    classify, sms = classify_document_with_multiple_rules(scan_result, rul)

    # Determine the label text based on the classification
    if classify == "Confidential":
        label_text = "Tài liệu Mật của BIDV. Cấm sao chép, in ấn dưới mọi hình thức!"
    elif classify == "Internal":
        label_text = "Tài liệu Nội bộ của BIDV. Cấm sao chép, in ấn dưới mọi hình thức!"
    else:
        label_text = ""

    # Access the first section of the document to modify the footer
    section = document.sections[0]

    # Set the layout margins
    section.top_margin = Cm(2)
    section.left_margin = Cm(3)
    section.bottom_margin = Cm(2)
    section.right_margin = Cm(2)

    # Access the footer of the section
    footer = section.footer

    # Remove all existing paragraphs in the footer to ensure it's overwritten
    for element in footer._element.xpath('.//w:p'):
        element.getparent().remove(element)

    # Add a new paragraph for the label and page number
    paragraph = footer.add_paragraph()

    # Calculate the right margin position for the page number
    right_margin_position = section.page_width - \
        section.right_margin - section.left_margin
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        right_margin_position, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES
    )

    # Add the label text (left-aligned) to the footer
    run_label = paragraph.add_run(label_text)
    run_label.font.name = 'Times New Roman'
    run_label.font.size = Pt(12)

    # Add a tab to position the page number on the right side
    run_label.add_tab()

    # Add the page number field (aligned to the right tab stop)
    run_page = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar')  # Begin field
    fldChar1.set(qn('w:fldCharType'), 'begin')

    instrText = OxmlElement('w:instrText')  # Field instruction text
    instrText.text = "PAGE"

    fldChar2 = OxmlElement('w:fldChar')  # Separate field
    fldChar2.set(qn('w:fldCharType'), 'separate')

    fldChar3 = OxmlElement('w:fldChar')  # End field
    fldChar3.set(qn('w:fldCharType'), 'end')

    # Append the field elements for the page number
    run_page._r.append(fldChar1)
    run_page._r.append(instrText)
    run_page._r.append(fldChar2)
    run_page._r.append(fldChar3)

    # Set the font for the page number
    run_page.font.name = 'Times New Roman'
    run_page.font.size = Pt(12)

    # Align the paragraph to the left (default behavior)
    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Save the document with the new footer
    document.save(file_path)

    return label_text


def label_xlsx_file_footer(file_path, classify):
    """
    Add a footer label to an Excel file based on the scan results.


    Parameters:
    - file_path: Path to the Excel file.
    - classify: Classification of the document ('Confidential', 'Internal', etc.).


    Returns:
    - str: Label text applied to the document.
    """
    # Scan the file to classify it
    scan_result = scan_file(file_path)
    rul = define_rules()
    classify, sms = classify_document_with_multiple_rules(scan_result, rul)

    # Determine the label text based on the classification
    if classify == "Confidential":
        label_text = "Tài liệu Mật của BIDV. Cấm sao chép, in ấn dưới mọi hình thức!"
    elif classify == "Internal":
        label_text = "Tài liệu Nội bộ của BIDV. Cấm sao chép, in ấn dưới mọi hình thức!"
    else:
        label_text = ""

    # Load the Excel workbook
    workbook = load_workbook(file_path)

    # Add the label to the footer of each worksheet
    for sheet in workbook.worksheets:
        # Construct the new footer with label on the left and page number on the right
        new_footer = f"&L{label_text} &RTrang &P"

        # Set the new footer text, font, and size
        sheet.oddFooter.center.text = new_footer
        sheet.oddFooter.center.size = 12
        sheet.oddFooter.center.font = "Times New Roman"

    # Save the modified Excel workbook
    workbook.save(file_path)

    return label_text



def edit_label_docx_file(file_path, label_text):
    # Load the DOCX document
    document = Document(file_path)

    # Access the first section of the document to modify the footer
    section = document.sections[0]

    # Set the layout margins
    section.top_margin = Cm(2)
    section.left_margin = Cm(3)
    section.bottom_margin = Cm(2)
    section.right_margin = Cm(2)

    # Access the footer of the section
    footer = section.footer

    # Remove all existing paragraphs in the footer to ensure it's overwritten
    for element in footer._element.xpath('.//w:p'):
        element.getparent().remove(element)

    # Add a new paragraph for the label and page number
    paragraph = footer.add_paragraph()

    # Calculate the right margin position for the page number
    right_margin_position = section.page_width - \
        section.right_margin - section.left_margin
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        right_margin_position, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES
    )

    # Add the label text (left-aligned) to the footer
    run_label = paragraph.add_run(label_text)
    run_label.font.name = 'Times New Roman'
    run_label.font.size = Pt(12)

    # Add a tab to position the page number on the right side
    run_label.add_tab()

    # Add the page number field (aligned to the right tab stop)
    run_page = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar')  # Begin field
    fldChar1.set(qn('w:fldCharType'), 'begin')

    instrText = OxmlElement('w:instrText')  # Field instruction text
    instrText.text = "PAGE"

    fldChar2 = OxmlElement('w:fldChar')  # Separate field
    fldChar2.set(qn('w:fldCharType'), 'separate')

    fldChar3 = OxmlElement('w:fldChar')  # End field
    fldChar3.set(qn('w:fldCharType'), 'end')

    # Append the field elements for the page number
    run_page._r.append(fldChar1)
    run_page._r.append(instrText)
    run_page._r.append(fldChar2)
    run_page._r.append(fldChar3)

    # Set the font for the page number
    run_page.font.name = 'Times New Roman'
    run_page.font.size = Pt(12)

    # Align the paragraph to the left (default behavior)
    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Save the document with the new footer
    document.save(file_path)

    return label_text


def edit_label_xlsx_file(file_path, label_text):
    # Load the Excel workbook
    workbook = load_workbook(file_path)

    # Add the label to the footer of each worksheet
    for sheet in workbook.worksheets:
        # Construct the new footer with label on the left and page number on the right
        new_footer = f"&L{label_text} &R &P"

        # Set the new footer text, font, and size
        sheet.oddFooter.center.text = new_footer
        sheet.oddFooter.center.size = 12
        sheet.oddFooter.center.font = "Times New Roman"

    # Save the modified Excel workbook
    workbook.save(file_path)

    return label_text