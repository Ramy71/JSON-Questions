import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuestionType(Enum):
    """Enum for supported question types"""
    MCQ = "mcq"
    MRQ = "mrq"
    STRING = "string"
    OQ = "oq"
    GAP_TEXT = "gapText"
    MATCHING = "matching"
    INPUT_BOX = "input_box"
    FRQ = "frq"
    FRQ_AI = "frq_ai"

class Language(Enum):
    """Enum for supported languages"""
    ARABIC = "ar"
    ENGLISH = "en"

@dataclass
class ProcessingStats:
    """Statistics for bulk processing operations"""
    total_questions: int = 0
    successful: int = 0
    failed: int = 0
    generated_files: List[str] = None
    
    def __post_init__(self):
        if self.generated_files is None:
            self.generated_files = []

class QuestionProcessor:
    """Enhanced question processing system with improved error handling and modularity"""
    
    # Expanded Arabic LaTeX mapping with better organization
    ARABIC_LATEX_MAP = {
        # Functions and operators
        "F(x)": "\\dotlessqaft (\\seen)",
        "Q'": "\\dotlessnoont \\prime",
        
        # Single characters - uppercase
        'N': '\\tah', 'Z': '\\sadt', 'Q': '\\dotlessnoont', 'X': '\\seent',
        'Y': '\\sadt', 'A': '\\alt{\\alef}', 'B': '\\beh', 'C': '\\jeemi',
        'D': '\\dal', 'E': '\\hehi', 'F': '\\waw', 'M': '\\meem',
        'K': '\\kaf', 'L': '\\lam', 'O': '\\waw', 'R': '\\haht',
        
        # Single characters - lowercase
        'x': '\\seen', 'y': '\\sad', 'z': '\\ain', 'n': '\\noon',
        's': '\\feh', 'r': '\\aint',
    }
    
    def __init__(self, output_dir: str = "generated_questions"):
        """Initialize the processor with configurable output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.stats = ProcessingStats()
        
    def get_current_timestamp(self) -> str:
        """Get current timestamp in standardized format"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def convert_to_arabic_latex(self, equation: str) -> str:
        """
        Enhanced function to convert equations to Arabic LaTeX with better error handling
        """
        if not equation or not isinstance(equation, str):
            logger.warning(f"Invalid equation input: {equation}")
            return str(equation) if equation else ""
        
        try:
            # Protect existing LaTeX commands
            latex_commands = re.findall(r'(\\[a-zA-Z]+(?:\{[^}]*\})?)', equation)
            protected_equation = equation
            
            # Replace commands with placeholders
            for i, command in enumerate(latex_commands):
                placeholder = f'__LATEX_CMD_{i}__'
                protected_equation = protected_equation.replace(command, placeholder, 1)
            
            # Process character mappings (longest first to avoid partial matches)
            sorted_keys = sorted(self.ARABIC_LATEX_MAP.keys(), key=len, reverse=True)
            
            # Split by spaces and process each part
            parts = protected_equation.split(' ')
            processed_parts = []
            
            for part in parts:
                # Check for exact matches first
                if part in sorted_keys:
                    processed_parts.append(self.ARABIC_LATEX_MAP[part])
                else:
                    # Check for partial matches within the part
                    processed_part = part
                    for key in sorted_keys:
                        if key in processed_part:
                            processed_part = processed_part.replace(key, self.ARABIC_LATEX_MAP[key])
                    processed_parts.append(processed_part)
            
            result = ' '.join(processed_parts)
            
            # Restore LaTeX commands
            for i, command in enumerate(latex_commands):
                placeholder = f'__LATEX_CMD_{i}__'
                result = result.replace(placeholder, command, 1)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Arabic LaTeX conversion: {e}")
            return equation
    
    def create_math_field(self, equation: str, language: Language, force_en: bool = False) -> str:
        """
        Enhanced math field creation with better validation
        """
        if not equation:
            return ""
        
        try:
            is_arabic = language == Language.ARABIC and not force_en
            latex_value = self.convert_to_arabic_latex(equation) if is_arabic else equation
            locale_attrs = ' locale="ar" lang="ar"' if is_arabic else ' locale="en"'
            
            # Better HTML escaping
            processed_value = (latex_value
                             .replace('&', '&amp;')
                             .replace('<', '&lt;')
                             .replace('>', '&gt;')
                             .replace('"', '&quot;')
                             .replace("'", '&#39;'))
            
            return (f'<span class="LexicalTheme__math--inline" data-node-type="math" '
                   f'data-node-variation="inline">'
                   f'<math-field default-mode="inline-math" read-only="true" '
                   f'value="{processed_value}"{locale_attrs}></math-field></span>')
        
        except Exception as e:
            logger.error(f"Error creating math field for equation '{equation}': {e}")
            return f'<span class="error">Math field error: {equation}</span>'
    
    def process_text_for_html(self, text: str, language: Language) -> str:
        """
        Enhanced text processing with better error handling and validation
        """
        if not text:
            return ""
        
        try:
            direction = ' dir="rtl"' if language == Language.ARABIC else ''
            blank_html = '<span data-node-type="blank-line" data-node-variation="space">&nbsp;</span>'
            processed_text = text.replace("_____", blank_html)

                        
            # Enhanced regex for math segments with better validation
            math_pattern = r'(``[^`]*``|`[^`]*`)'
            parts = re.split(math_pattern, processed_text)
            
            final_html_content = ""
            
            for part in parts:
                if not part:
                    continue
                
                # Handle override math (double backticks)
                if part.startswith('``') and part.endswith('``'):
                    math_content = part[2:-2].strip()
                    if math_content:
                        final_html_content += self.create_math_field(math_content, language, force_en=True)
                
                # Handle regular math (single backticks)
                elif part.startswith('`') and part.endswith('`'):
                    math_content = part[1:-1].strip()
                    if math_content:
                        final_html_content += self.create_math_field(math_content, language)
                
                # Handle plain text
                else:
                                # Handle visual blanks
                    # Better HTML escaping for text content
                    escaped_text = (part
                                  .replace('&', '&amp;')
                                  .replace('<', '&lt;')
                                  .replace('>', '&gt;'))
                    final_html_content += f'<span style="white-space: pre-wrap;">{escaped_text}</span>'
            
            return f'<p class="LexicalTheme__paragraph"{direction}>{final_html_content}</p>'
        
        except Exception as e:
            logger.error(f"Error processing text for HTML: {e}")
            return f'<p class="error">Text processing error: {text[:50]}...</p>'
    
    def validate_metadata(self, metadata: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate required metadata fields"""
        required_fields = ['id', 'language']
        errors = []
        
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate language
        if 'language' in metadata:
            try:
                Language(metadata['language'])
            except ValueError:
                errors.append(f"Invalid language: {metadata['language']}")
        
        # Validate ID is numeric
        if 'id' in metadata:
            try:
                int(metadata['id'])
            except ValueError:
                errors.append(f"ID must be numeric: {metadata['id']}")
        
        return len(errors) == 0, errors
    
    def create_base_json_structure(self, metadata: Dict[str, str]) -> Dict[str, Any]:
        """Create the base JSON structure with validated metadata"""
        language = Language(metadata['language'])
        question_id = int(metadata['id'])
        mapped_id = question_id
        
        if language == Language.ARABIC and 'mapped_id' in metadata:
            mapped_id = question_id
            question_id = int(metadata['mapped_id'])
        
        dialect_map = {
            Language.ARABIC: ["modern_standard"],
            Language.ENGLISH: ["american", "british"]
        }
        
        return {
            "parts": [],
            "statement": None,
            "instance_number": 1,
            "metadata": {
                "id": question_id,
                "mapped_id": mapped_id,
                "category": metadata.get('category', 'exam'),
                "language": language.value,
                "country": metadata.get('country', 'eg'),
                "dialect": dialect_map[language],
                "source_id": {
                    "value": 182136230818,
                    "page_number": None
                },
                "description": metadata.get('description', ''),
                "example_id": None,
                "has_example": False,
                "instances_count": 1,
                "publication_date": self.get_current_timestamp(),
                "parts_count": 0  # Will be updated later
            }
        }
    
    def process_mcq_mrq_part(self, content: Dict[str, str], language: Language) -> Dict[str, Any]:
        """Process MCQ/MRQ question parts"""
        choices = []
        if 'choices' not in content:
            raise ValueError("MCQ/MRQ questions must have choices")
        
        choices_lines = [line.strip() for line in content['choices'].strip().split('\n') if line.strip()]
        
        for j, choice_line in enumerate(choices_lines):
            is_key = choice_line.startswith('*')
            text = choice_line[1:].strip() if is_key else choice_line.strip()
            
            choices.append({
                "type": "key" if is_key else "distractor",
                "html_content": self.process_text_for_html(text, language),
                "values": [],
                "unit": None,
                "index": j,
                "fixed_order": j + 1,
                "last_order": False
            })
        
        return {"choices": choices}
    
    def process_string_part(self, content: Dict[str, str], metadata: Dict[str, str], 
                          part_metadata: Dict[str, str], language: Language) -> Dict[str, Any]:
        """Process string question parts"""
        if 'answer' not in content:
            raise ValueError("String questions must have an answer")
        
        result = {
            "choices": None,
            "answer": [self.process_text_for_html(content['answer'].strip(), language)]
        }
        
        # Add AI template if specified
        ai_id = part_metadata.get('ai_template_id') or metadata.get('ai_template_id')
        if ai_id:
            result["ai"] = {"ai_template_id": ai_id}
        
        return result
    
    def process_oq_part(self, content: Dict[str, str], language: Language) -> Dict[str, Any]:
        """Process ordering question parts"""
        if 'choices' not in content:
            raise ValueError("OQ questions must have choices")
        
        choices = []
        oq_lines = [line.strip() for line in content['choices'].strip().split('\n') if line.strip()]
        
        for j, line in enumerate(oq_lines):
            choices.append({
                "type": "distractor",
                "html_content": self.process_text_for_html(line, language),
                "correct_order": j + 1,
                "values": [],
                "unit": None,
                "index": j,
                "fixed_order": j + 1,
                "last_order": False
            })
        
        return {
            "direction": "vertical",
            "choices": choices
        }
    
    def process_gap_text_part(self, content: Dict[str, str], language: Language) -> Dict[str, Any]:
        """Process gap text question parts"""
        if 'gaps' not in content or 'stem' not in content:
            raise ValueError("Gap text questions must have gaps and stem")
        
        gap_text_keys = []
        gap_lines = [line.strip() for line in content['gaps'].strip().split('\n') if line.strip()]
        
        for j, line in enumerate(gap_lines):
            gap_text_keys.append({
                "value": line,
                "correct_order": j + 1
            })
        
        # Replace [BLANK] with HTML gap element
        stem_html_gap = '<span data-node-type="blank-line" data-node-variation="gap">&nbsp;</span>'
        processed_stem = content['stem'].strip().replace("[BLANK]", stem_html_gap)
        
        return {
            "choices": [],
            "gap_text_keys": gap_text_keys,
            "stem": self.process_text_for_html(processed_stem, language)
        }
    
    def process_matching_part(self, content: Dict[str, str], language: Language) -> Dict[str, Any]:
        """Process matching question parts"""
        if 'matching_pairs' not in content:
            raise ValueError("Matching questions must have matching_pairs")
        
        choices = []
        pair_lines = [line.strip() for line in content['matching_pairs'].strip().split('\n') if line.strip()]
        
        for j, line in enumerate(pair_lines):
            if '|' not in line:
                raise ValueError(f"Matching pair must contain '|' separator: {line}")
            
            group1_text, group2_text = line.split('|', 1)
            
            # Group 1 items
            choices.append({
                "type": "distractor",
                "html_content": self.process_text_for_html(group1_text.strip(), language),
                "group": 1,
                "correct_order": j + 1,
                "values": [],
                "unit": None,
                "index": j,
                "fixed_order": j + 1,
                "last_order": False
            })
            
            # Group 2 items
            choices.append({
                "type": "distractor",
                "html_content": self.process_text_for_html(group2_text.strip(), language),
                "group": 2,
                "correct_order": j + 1,
                "values": [],
                "unit": None,
                "index": j + len(pair_lines),
                "fixed_order": j + 1 + len(pair_lines),
                "last_order": False
            })
        
        return {"choices": choices}
    
    def process_input_box_part(self, content: Dict[str, str]) -> Dict[str, Any]:
        """Process input box question parts"""
        if 'answer' not in content:
            raise ValueError("Input box questions must have an answer")
        
        answer_parts = content['answer'].strip().split('|')
        value = answer_parts[0].strip()
        unit = answer_parts[1].strip() if len(answer_parts) > 1 else None
        
        return {
            "choices": [],
            "answer": {
                "value": value,
                "unit": unit,
                "constrains": {"type": "integer"}
            }
        }
    
    def process_frq_part(self, content: Dict[str, str], metadata: Dict[str, str],
                        part_metadata: Dict[str, str], language: Language, 
                        question_type: QuestionType) -> Dict[str, Any]:
        """Process FRQ and FRQ_AI question parts"""
        if 'answer' not in content:
            raise ValueError("FRQ questions must have an answer")
        
        result = {
            "choices": [],
            "answer": self.process_text_for_html(content['answer'].strip(), language)
        }
        
        if question_type == QuestionType.FRQ_AI:
            ai_id = part_metadata.get('ai_template_id') or metadata.get('ai_template_id')
            if not ai_id:
                raise ValueError("'ai_template_id' is required for frq_ai type")
            result["ai"] = {"ai_template_id": ai_id}
        
        return result
    
    def process_question_part(self, part_block: str, part_counter: int, 
                            metadata: Dict[str, str], language: Language) -> Optional[Dict[str, Any]]:
        """Process a single question part with comprehensive error handling"""
        try:
            part_metadata, content, current_tag = {}, {}, None
            
            # Parse part block
            for line in part_block.strip().split('\n'):
                tag_match = re.match(r'^\[([A-Z_]+)\]$', line)
                meta_match = re.match(r'^([a-z_]+):\s*(.*)', line)
                
                if tag_match:
                    current_tag = tag_match.group(1).lower()
                    content[current_tag] = ""
                elif meta_match and current_tag is None:
                    part_metadata[meta_match.group(1)] = meta_match.group(2)
                elif current_tag and line.strip():
                    content[current_tag] += line + "\n"
            
            # Clean up content
            for key in content:
                content[key] = content[key].strip()
            
            # Determine question type
            part_type_str = part_metadata.get('type') or metadata.get('type')
            if not part_type_str:
                raise ValueError("Question type not specified")
            
            try:
                question_type = QuestionType(part_type_str)
            except ValueError:
                raise ValueError(f"Unsupported question type: {part_type_str}")
            
            # Create base part structure
            part = {
                "n": part_counter,
                "type": question_type.value,
                "subtype": None,
                "standalone": False
            }
            
            # Process stem if present
            if 'stem' in content:
                part["stem"] = self.process_text_for_html(content['stem'], language)
            
            # Process based on question type
            if question_type in [QuestionType.MCQ, QuestionType.MRQ]:
                part.update(self.process_mcq_mrq_part(content, language))
            
            elif question_type == QuestionType.STRING:
                part.update(self.process_string_part(content, metadata, part_metadata, language))
            
            elif question_type == QuestionType.OQ:
                part.update(self.process_oq_part(content, language))
            
            elif question_type == QuestionType.GAP_TEXT:
                gap_result = self.process_gap_text_part(content, language)
                part["stem"] = gap_result["stem"]  # Override stem for gap text
                part["choices"] = gap_result["choices"]
                part["gap_text_keys"] = gap_result["gap_text_keys"]
            
            elif question_type == QuestionType.MATCHING:
                part.update(self.process_matching_part(content, language))
            
            elif question_type == QuestionType.INPUT_BOX:
                part.update(self.process_input_box_part(content))
            
            elif question_type in [QuestionType.FRQ, QuestionType.FRQ_AI]:
                part.update(self.process_frq_part(content, metadata, part_metadata, language, question_type))
            
            return part
        
        except Exception as e:
            logger.error(f"Error processing part {part_counter}: {e}")
            raise
    
    def process_single_question(self, block: str, question_number: int) -> Optional[str]:
        """Process a single question block and return the generated filename"""
        try:
            logger.info(f"Processing Question #{question_number}...")
            
            lines = [line.rstrip() for line in block.strip().split('\n')]
            metadata = {}
            metadata_end_index = 0
            
            # Parse metadata
            for j, line in enumerate(lines):
                if line.startswith('['):
                    metadata_end_index = j
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            # Validate metadata
            is_valid, errors = self.validate_metadata(metadata)
            if not is_valid:
                raise ValueError(f"Metadata validation failed: {', '.join(errors)}")
            
            language = Language(metadata['language'])
            final_json = self.create_base_json_structure(metadata)
            
            # Parse content
            content_str = '\n'.join(lines[metadata_end_index:])
            
            # Handle statement and parts
            if '[STATEMENT]' in content_str and '[PART]' in content_str:
                statement_content, parts_str = content_str.split('[PART]', 1)
                statement_text = statement_content.replace('[STATEMENT]', '').strip()
                if statement_text:
                    final_json["statement"] = self.process_text_for_html(statement_text, language)
                
                part_blocks_raw = ('[PART]' + parts_str).split('[PART]')
                part_blocks = [p.strip() for p in part_blocks_raw if p.strip()]
            else:
                part_blocks = [content_str] if content_str.strip() else []
            
            # Process parts
            for part_counter, part_block in enumerate(part_blocks, 1):
                if not part_block.strip():
                    continue
                
                part = self.process_question_part(part_block, part_counter, metadata, language)
                if part:
                    final_json['parts'].append(part)
            
            # Update parts count
            final_json['metadata']['parts_count'] = len(final_json['parts'])
            
            # Validate final structure
            if not final_json['parts']:
                raise ValueError("No valid parts found in question")
            
            # Save to file
            file_name = f"{metadata['id']}.json"
            file_path = self.output_dir / file_name
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(final_json, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Successfully created {file_name}")
            return file_name
            
        except Exception as e:
            logger.error(f"❌ Error processing Question #{question_number}: {e}")
            return None
    
    def process_google_doc(self, doc_content: str) -> ProcessingStats:
        """
        Enhanced bulk processing with comprehensive statistics and error handling
        """
        logger.info("--- Starting Bulk Processing ---")
        
        # Reset statistics
        self.stats = ProcessingStats()
        
        # Split into question blocks
        question_blocks = [block.strip() for block in doc_content.strip().split('---\n') if block.strip()]
        self.stats.total_questions = len(question_blocks)
        
        logger.info(f"Found {self.stats.total_questions} question blocks to process")
        
        for i, block in enumerate(question_blocks, 1):
            result = self.process_single_question(block, i)
            
            if result:
                self.stats.successful += 1
                self.stats.generated_files.append(result)
            else:
                self.stats.failed += 1
        
        # Log final statistics
        logger.info("--- Bulk Processing Complete ---")
        logger.info(f"Total Questions: {self.stats.total_questions}")
        logger.info(f"Successful: {self.stats.successful}")
        logger.info(f"Failed: {self.stats.failed}")
        logger.info(f"Success Rate: {(self.stats.successful/self.stats.total_questions*100):.1f}%")
        
        return self.stats
