"""
Game Asset Analyzer - External tool for checking item usage and existence
Enhanced version with detailed missing item location tracking
"""

import ast
import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import fnmatch
import argparse
import difflib


@dataclass
class ItemReference:
    """Represents a reference to an item in code"""
    file_path: str
    line_number: int
    column: int
    context: str  # The line of code containing the reference
    method_used: str  # e.g., 'get_item', 'get_items_by_type', etc.


@dataclass
class ConfigReference:
    """Represents a reference to an item in a config file"""
    file_path: str
    item_name: str
    context: str  # Additional context about where in the config
    count: int = 1  # How many times the item appears in this config


@dataclass
class SuggestionMatch:
    """Represents a suggested item match with similarity score"""
    item_name: str
    similarity: float
    match_type: str  # 'exact_substring', 'fuzzy', 'phonetic', etc.


@dataclass
class MissingItemInfo:
    """Information about a missing item including where it's referenced"""
    item_name: str
    code_references: List[ItemReference]
    config_references: List[ConfigReference]
    suggested_matches: List[SuggestionMatch]
    
    @property
    def total_references(self) -> int:
        return len(self.code_references) + len(self.config_references)


@dataclass
class DuplicateItemInfo:
    """Information about an item name that appears in multiple store files"""
    item_name: str
    file_paths: List[str]  # All files that define this item name

    @property
    def count(self) -> int:
        return len(self.file_paths)


@dataclass
class AnalysisReport:
    """Contains the results of the analysis"""
    item_name: str
    exists_in_store: bool
    references: List[ItemReference]
    file_path_in_store: Optional[str] = None


class GitignoreParser:
    """Parses .gitignore patterns to determine which files to skip"""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.patterns = []
        self._load_gitignore()
    
    def _load_gitignore(self):
        """Load patterns from .gitignore file"""
        gitignore_path = self.root_dir / '.gitignore'
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.patterns.append(line)
        
        # Add common patterns to ignore
        default_patterns = [
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '*.egg-info',
            '.git',
            '.venv',
            'venv',
            '.env',
            'node_modules',
            '.pytest_cache'
        ]
        self.patterns.extend(default_patterns)
    
    def should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on patterns"""
        relative_path = file_path.relative_to(self.root_dir)
        path_str = str(relative_path)
        
        for pattern in self.patterns:
            if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return True
            
            # Check if any parent directory matches the pattern
            for parent in relative_path.parents:
                if fnmatch.fnmatch(str(parent), pattern):
                    return True
        
        return False




class ConfigAnalyzer:
    """Analyzes configuration files for item references"""
    
    def __init__(self):
        self.config_patterns = []
    
    def add_config_pattern(self, directory: str, pattern_type: str, **kwargs):
        """
        Add a configuration pattern to analyze
        
        Args:
            directory: Path to directory containing config files
            pattern_type: Type of pattern ('room_configs' or 'nested_items')
            **kwargs: Additional pattern-specific parameters
        """
        self.config_patterns.append({
            'directory': Path(directory),
            'type': pattern_type,
            'params': kwargs
        })
    
    def analyze_room_configs(self, directory: Path, ignore_key: str = "initial_room") -> Dict[str, List[ConfigReference]]:
        """
        Analyze room config files where all keys except ignore_key contain item lists
        
        Returns: Dict mapping item_name -> list of ConfigReference objects
        """
        item_references = defaultdict(list)
        
        if not directory.exists():
            print(f"Warning: Config directory '{directory}' does not exist")
            return dict(item_references)
        
        for config_file in directory.glob('*.json'):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                items_found = defaultdict(int)
                context_info = []
                
                for key, value in data.items():
                    if key == ignore_key:
                        continue
                    
                    if isinstance(value, list):
                        # Assume all list items are item names (strings)
                        for item in value:
                            if isinstance(item, str):
                                items_found[item] += 1
                                context_info.append(f"in '{key}' list")
                    elif isinstance(value, str):
                        # Single item as string
                        items_found[value] += 1
                        context_info.append(f"as '{key}' value")
                
                # Create ConfigReference objects
                for item_name, count in items_found.items():
                    config_ref = ConfigReference(
                        file_path=str(config_file),
                        item_name=item_name,
                        context=f"Room config: found {count} time(s)",
                        count=count
                    )
                    item_references[item_name].append(config_ref)
                    
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not parse config file '{config_file}': {e}")
        
        return dict(item_references)
    
    def analyze_nested_items(self, directory: Path, items_key: str = "items") -> Dict[str, List[ConfigReference]]:
        """
        Analyze config files with nested dictionaries containing items lists
        
        Structure expected:
        {
            "config_name_1": {
                "items": ["item1", "item2", ...]
            },
            "config_name_2": {
                "items": ["item3", "item4", ...]
            }
        }
        
        Returns: Dict mapping item_name -> list of ConfigReference objects
        """
        item_references = defaultdict(list)
        
        if not directory.exists():
            print(f"Warning: Config directory '{directory}' does not exist")
            return dict(item_references)
        
        for config_file in directory.glob('*.json'):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                items_found = defaultdict(list)  # item_name -> list of config sections
                
                # Iterate through the outer dictionary
                for config_name, config_data in data.items():
                    if isinstance(config_data, dict) and items_key in config_data:
                        items_list = config_data[items_key]
                        if isinstance(items_list, list):
                            for item in items_list:
                                if isinstance(item, str):
                                    items_found[item].append(config_name)
                
                # Create ConfigReference objects
                for item_name, config_sections in items_found.items():
                    count = len(config_sections)
                    context = f"Nested config: in sections {', '.join(config_sections)}"
                    config_ref = ConfigReference(
                        file_path=str(config_file),
                        item_name=item_name,
                        context=context,
                        count=count
                    )
                    item_references[item_name].append(config_ref)
                    
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not parse config file '{config_file}': {e}")
        
        return dict(item_references)
    
    def analyze_all_configs(self) -> Dict[str, List[ConfigReference]]:
        """Analyze all configured patterns and return combined results"""
        all_references = defaultdict(list)
        
        for pattern in self.config_patterns:
            directory = pattern['directory']
            pattern_type = pattern['type']
            params = pattern['params']
            
            print(f"Analyzing {pattern_type} configs in {directory}")
            
            if pattern_type == 'room_configs':
                ignore_key = params.get('ignore_key', 'initial_room')
                references = self.analyze_room_configs(directory, ignore_key)
            elif pattern_type == 'nested_items':
                items_key = params.get('items_key', 'items')
                references = self.analyze_nested_items(directory, items_key)
            else:
                print(f"Warning: Unknown pattern type '{pattern_type}'")
                continue
            
            # Merge references
            for item_name, config_refs in references.items():
                all_references[item_name].extend(config_refs)
        
        return dict(all_references)
    
    def get_all_referenced_items(self) -> Set[str]:
        """Get a set of all item names referenced in configs"""
        all_references = self.analyze_all_configs()
        return set(all_references.keys())


class ItemStoreASTVisitor(ast.NodeVisitor):
    """AST visitor to find item store method calls"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.references = []
        self.lines = []
    
    def set_source_lines(self, lines: List[str]):
        """Set the source code lines for context"""
        self.lines = lines
    
    def visit_Call(self, node: ast.Call):
        """Visit function calls to find item store methods"""
        # Look for method calls like store.get_item(), store.get_items_by_type(), etc.
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            
            # Check if it's an ItemStore method
            item_store_methods = {
                'get_item', 'get_items_by_type', 'find_items', 
                'add_item_definition', 'save_item_to_file'
            }
            
            if method_name in item_store_methods:
                # Extract item names from arguments
                item_names = self._extract_item_names(node, method_name)
                
                for item_name in item_names:
                    context = self._get_context(node.lineno)
                    reference = ItemReference(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        column=node.col_offset,
                        context=context,
                        method_used=method_name
                    )
                    self.references.append((item_name, reference))
        
        self.generic_visit(node)
    
    def _extract_item_names(self, node: ast.Call, method_name: str) -> List[str]:
        """Extract item names from method call arguments"""
        item_names = []
        
        if not node.args:
            return item_names
        
        # For most methods, the first argument is the item name(s)
        first_arg = node.args[0]
        
        if method_name == 'get_item':
            # Can be a single string or a list of strings
            names = self._extract_string_values(first_arg)
            item_names.extend(names)
        
        elif method_name in ['add_item_definition', 'save_item_to_file']:
            # First argument is item_name for save_item_to_file
            # For add_item_definition, we'd need to look at the dict structure
            if method_name == 'save_item_to_file':
                names = self._extract_string_values(first_arg)
                item_names.extend(names)
        
        return item_names
    
    def _extract_string_values(self, node: ast.AST) -> List[str]:
        """Extract string values from AST nodes"""
        values = []
        
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
        elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
            values.append(node.s)
        elif isinstance(node, ast.List):
            for elt in node.elts:
                values.extend(self._extract_string_values(elt))
        elif isinstance(node, ast.Name):
            # Variable reference - we can't statically determine the value
            # but we can note it as a dynamic reference
            values.append(f"<variable:{node.id}>")
        
        return values
    
    def _get_context(self, line_number: int) -> str:
        """Get the source code line for context"""
        if 1 <= line_number <= len(self.lines):
            return self.lines[line_number - 1].strip()
        return ""


class CodebaseAnalyzer:
    """Analyzes the codebase for item references"""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.gitignore_parser = GitignoreParser(root_dir)
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the codebase"""
        python_files = []
        
        for file_path in self.root_dir.rglob('*.py'):
            if not self.gitignore_parser.should_ignore(file_path):
                python_files.append(file_path)
        
        return python_files
    
    def analyze_file(self, file_path: Path) -> List[Tuple[str, ItemReference]]:
        """Analyze a single Python file for item references"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
                lines = source.splitlines()
            
            tree = ast.parse(source, filename=str(file_path))
            visitor = ItemStoreASTVisitor(str(file_path))
            visitor.set_source_lines(lines)
            visitor.visit(tree)
            
            return visitor.references
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return []
    
    def find_all_item_references(self) -> Dict[str, List[ItemReference]]:
        """Find all item references in the codebase"""
        all_references = defaultdict(list)
        python_files = self.find_python_files()
        
        print(f"Analyzing {len(python_files)} Python files...")
        
        for file_path in python_files:
            references = self.analyze_file(file_path)
            for item_name, reference in references:
                # Skip variable references for now
                if not item_name.startswith('<variable:'):
                    all_references[item_name].append(reference)
        
        return dict(all_references)


class FuzzyMatcher:
    """Provides fuzzy matching suggestions for missing items"""
    
    def __init__(self, existing_items: List[str]):
        self.existing_items = existing_items
        self.existing_items_lower = [item.lower() for item in existing_items]
    
    def find_suggestions(self, missing_item: str, max_suggestions: int = 5, min_similarity: float = 0.4) -> List[SuggestionMatch]:
        """
        Find suggested matches for a missing item using multiple strategies
        
        Args:
            missing_item: The missing item name to find suggestions for
            max_suggestions: Maximum number of suggestions to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        
        Returns:
            List of SuggestionMatch objects sorted by similarity (best first)
        """
        suggestions = []
        missing_lower = missing_item.lower()
        
        # Strategy 1: Exact substring matches (highest priority)
        for item in self.existing_items:
            if missing_lower in item.lower() or item.lower() in missing_lower:
                similarity = min(len(missing_lower), len(item.lower())) / max(len(missing_lower), len(item.lower()))
                suggestions.append(SuggestionMatch(
                    item_name=item,
                    similarity=similarity + 0.2,  # Boost substring matches
                    match_type='substring'
                ))
        
        # Strategy 2: Difflib sequence matching (handles typos well)
        for item in self.existing_items:
            similarity = difflib.SequenceMatcher(None, missing_lower, item.lower()).ratio()
            if similarity >= min_similarity:
                # Check if we already have this item from substring matching
                existing_match = next((s for s in suggestions if s.item_name == item), None)
                if existing_match:
                    # Update similarity if fuzzy is better
                    if similarity > existing_match.similarity - 0.2:  # Account for substring boost
                        existing_match.similarity = max(existing_match.similarity, similarity + 0.1)
                        existing_match.match_type = 'substring+fuzzy'
                else:
                    suggestions.append(SuggestionMatch(
                        item_name=item,
                        similarity=similarity,
                        match_type='fuzzy'
                    ))
        
        # Strategy 3: Common transformations (plurals, common prefixes/suffixes)
        transformation_suggestions = self._find_transformation_matches(missing_item, min_similarity)
        for suggestion in transformation_suggestions:
            existing_match = next((s for s in suggestions if s.item_name == suggestion.item_name), None)
            if existing_match:
                existing_match.similarity = max(existing_match.similarity, suggestion.similarity)
                existing_match.match_type += '+transform'
            else:
                suggestions.append(suggestion)
        
        # Strategy 4: Word-based matching (for multi-word items)
        word_suggestions = self._find_word_based_matches(missing_item, min_similarity)
        for suggestion in word_suggestions:
            existing_match = next((s for s in suggestions if s.item_name == suggestion.item_name), None)
            if existing_match:
                existing_match.similarity = max(existing_match.similarity, suggestion.similarity)
                existing_match.match_type += '+words'
            else:
                suggestions.append(suggestion)
        
        # Sort by similarity (best first) and limit results
        suggestions.sort(key=lambda x: x.similarity, reverse=True)
        return suggestions[:max_suggestions]
    
    def _find_transformation_matches(self, missing_item: str, min_similarity: float) -> List[SuggestionMatch]:
        """Find matches using common transformations"""
        suggestions = []
        missing_lower = missing_item.lower()
        
        # Common transformations to try
        transformations = [
            # Plural/singular
            (lambda x: x + 's' if not x.endswith('s') else x[:-1]),
            (lambda x: x + 'es' if not x.endswith('es') else x[:-2]),
            # Common prefixes/suffixes
            (lambda x: 'magic_' + x if not x.startswith('magic_') else x[6:]),
            (lambda x: x + '_potion' if not x.endswith('_potion') else x[:-7]),
            (lambda x: x + '_sword' if not x.endswith('_sword') else x[:-6]),
            (lambda x: x + '_item' if not x.endswith('_item') else x[:-5]),
            # Underscore variations
            (lambda x: x.replace('_', '') if '_' in x else x.replace(' ', '_')),
            (lambda x: x.replace(' ', '_') if ' ' in x else x.replace('_', ' ')),
            # Case variations already handled by lower()
        ]
        
        for transform in transformations:
            try:
                transformed = transform(missing_lower)
                if transformed != missing_lower:  # Only if transformation actually changed something
                    for item in self.existing_items:
                        if transformed == item.lower():
                            suggestions.append(SuggestionMatch(
                                item_name=item,
                                similarity=0.9,  # High similarity for transformation matches
                                match_type='transformation'
                            ))
            except:
                continue  # Skip if transformation fails
        
        return suggestions
    
    def _find_word_based_matches(self, missing_item: str, min_similarity: float) -> List[SuggestionMatch]:
        """Find matches based on individual words (for compound item names)"""
        suggestions = []
        missing_words = set(missing_item.lower().replace('_', ' ').split())
        
        if len(missing_words) <= 1:
            return suggestions  # Skip single-word items
        
        for item in self.existing_items:
            item_words = set(item.lower().replace('_', ' ').split())
            
            if len(item_words) <= 1:
                continue  # Skip single-word existing items
            
            # Calculate word overlap similarity
            common_words = missing_words.intersection(item_words)
            if common_words:
                # Jaccard similarity with word overlap
                union_words = missing_words.union(item_words)
                word_similarity = len(common_words) / len(union_words)
                
                if word_similarity >= min_similarity:
                    suggestions.append(SuggestionMatch(
                        item_name=item,
                        similarity=word_similarity,
                        match_type='word_based'
                    ))
        
        return suggestions


class GameAssetAnalyzer:
    """Main analyzer class that combines ItemStore, codebase, and config analysis"""
    
    def __init__(self, code_root_dir: str, item_store_dir: str):
        # Import ItemStore from the provided code
        from item_store import ItemStore  # Assuming the ItemStore is in paste.py
        
        self.item_store = ItemStore(item_store_dir)
        self.item_store_dir = Path(item_store_dir)
        self.codebase_analyzer = CodebaseAnalyzer(code_root_dir)
        self.config_analyzer = ConfigAnalyzer()
        self.code_root_dir = Path(code_root_dir)
    
    def add_config_pattern(self, directory: str, pattern_type: str, **kwargs):
        """
        Add a configuration pattern to analyze
        
        Examples:
            # Room configs: all keys except 'initial_room' contain item lists
            analyzer.add_config_pattern('./configs/rooms', 'room_configs', ignore_key='initial_room')
            
            # Nested configs: dictionaries with 'items' key containing item lists
            analyzer.add_config_pattern('./configs/quests', 'nested_items', items_key='items')
        """
        self.config_analyzer.add_config_pattern(directory, pattern_type, **kwargs)
    
    def check_item_usage(self, item_name: str) -> AnalysisReport:
        """Check usage of a specific item across code and configs"""
        # Check if item exists in store
        item_data = self.item_store.get_item(item_name)
        exists_in_store = item_data is not None
        
        # Get file path from store if available
        file_path_in_store = None
        if hasattr(self.item_store, '_item_to_file_map'):
            file_path_in_store = self.item_store._item_to_file_map.get(item_name)
        
        # Find references in code
        all_references = self.codebase_analyzer.find_all_item_references()
        references = all_references.get(item_name, [])
        
        # Add references from config files
        config_references = self.config_analyzer.analyze_all_configs()
        if item_name in config_references:
            for config_ref in config_references[item_name]:
                # Create a pseudo-reference for config file
                item_ref = ItemReference(
                    file_path=config_ref.file_path,
                    line_number=0,  # Config files don't have meaningful line numbers for this
                    column=0,
                    context=config_ref.context,
                    method_used="config_reference"
                )
                references.append(item_ref)
        
        return AnalysisReport(
            item_name=item_name,
            exists_in_store=exists_in_store,
            references=references,
            file_path_in_store=file_path_in_store
        )
    
    def validate_item_exists(self, item_name: str) -> bool:
        """Check if an item exists in the store"""
        return self.item_store.get_item(item_name) is not None
    
    def find_orphaned_items(self) -> List[str]:
        """Find items that exist in store but are not used in code or configs"""
        all_items = self.item_store.get_all_items()
        code_references = self.codebase_analyzer.find_all_item_references()
        config_items = self.config_analyzer.get_all_referenced_items()
        
        # Combine code and config references
        all_referenced_items = set(code_references.keys()) | config_items
        
        orphaned = []
        for item in all_items:
            item_name = item.get('name')
            if item_name and item_name not in all_referenced_items:
                orphaned.append(item_name)
        
        return orphaned
    
    def find_missing_items(self) -> Dict[str, MissingItemInfo]:
        """Find items referenced in code/configs but not in store with detailed location info and suggestions"""
        code_references = self.codebase_analyzer.find_all_item_references()
        config_references = self.config_analyzer.analyze_all_configs()
        
        # Get all existing item names for fuzzy matching
        all_items = self.item_store.get_all_items()
        existing_item_names = [item.get('name') for item in all_items if item.get('name')]
        fuzzy_matcher = FuzzyMatcher(existing_item_names)
        
        missing_items = {}
        
        # Check code references
        for item_name, refs in code_references.items():
            if not self.validate_item_exists(item_name):
                suggestions = fuzzy_matcher.find_suggestions(item_name)
                missing_items[item_name] = MissingItemInfo(
                    item_name=item_name,
                    code_references=refs,
                    config_references=[],
                    suggested_matches=suggestions
                )
        
        # Check config references
        for item_name, config_refs in config_references.items():
            if not self.validate_item_exists(item_name):
                if item_name in missing_items:
                    # Add config references to existing missing item
                    missing_items[item_name].config_references.extend(config_refs)
                else:
                    # Create new missing item entry
                    suggestions = fuzzy_matcher.find_suggestions(item_name)
                    missing_items[item_name] = MissingItemInfo(
                        item_name=item_name,
                        code_references=[],
                        config_references=config_refs,
                        suggested_matches=suggestions
                    )
        
        return missing_items

    def find_duplicate_items(self) -> Dict[str, DuplicateItemInfo]:
        """
        Find items whose 'name' field appears in more than one store file.

        The item store may spread definitions across multiple JSON files.  If the
        same name is defined in two or more of those files the store will silently
        return whichever definition it loaded last, which can cause hard-to-track
        bugs.  This method surfaces every such collision so they can be resolved.

        Strategy
        --------
        1.  Walk every JSON file under the item_store_dir (recursively).
        2.  For each file, collect every top-level string value for a 'name' key,
            and also handle list-of-objects structures where each element may have
            a 'name' key.
        3.  Fall back to the ItemStore's own `get_all_items()` and its internal
            `_item_to_file_map` when available, because the store may apply its
            own loading logic (e.g. merging files, custom keys).
        4.  Report any name that maps to more than one distinct source file.

        Returns
        -------
        Dict mapping item_name -> DuplicateItemInfo for every duplicated name.
        """
        # ------------------------------------------------------------------
        # Primary strategy: use the store's own file-map if it exposes one.
        # ------------------------------------------------------------------
        name_to_files: Dict[str, List[str]] = defaultdict(list)

        if hasattr(self.item_store, '_item_to_file_map'):
            # _item_to_file_map: {item_name: file_path}  (only keeps the *last*
            # file that defined the name, so it can't expose duplicates by itself)
            # We still use it as a starting point but must supplement with a
            # full directory scan below.
            pass  # handled in the scan below

        # ------------------------------------------------------------------
        # Full scan: read every JSON file in the store directory directly so
        # we see *all* definitions, not just the winners.
        # ------------------------------------------------------------------
        if self.item_store_dir.exists():
            for json_file in self.item_store_dir.rglob('*.json'):
                try:
                    with open(json_file, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                except (json.JSONDecodeError, IOError) as exc:
                    print(f"Warning: Could not read store file '{json_file}': {exc}")
                    continue

                file_str = str(json_file)

                # Support three common store layouts:
                #   (a) A single object  {"name": "sword", ...}
                #   (b) A list of objects [{"name": "sword"}, {"name": "shield"}]
                #   (c) A dict of objects {"sword": {"name": "sword"}, ...}

                if isinstance(data, dict):
                    if 'name' in data and isinstance(data['name'], str):
                        # Layout (a)
                        name_to_files[data['name']].append(file_str)
                    else:
                        # Layout (c) – values are item dicts
                        for value in data.values():
                            if isinstance(value, dict) and 'name' in value and isinstance(value['name'], str):
                                name_to_files[value['name']].append(file_str)

                elif isinstance(data, list):
                    # Layout (b)
                    for entry in data:
                        if isinstance(entry, dict) and 'name' in entry and isinstance(entry['name'], str):
                            name_to_files[entry['name']].append(file_str)

        # ------------------------------------------------------------------
        # Also ask the store itself for all items (catches in-memory merges).
        # ------------------------------------------------------------------
        for item in self.item_store.get_all_items():
            item_name = item.get('name')
            if not item_name:
                continue
            # Use the store's own file map if present
            if hasattr(self.item_store, '_item_to_file_map'):
                store_file = self.item_store._item_to_file_map.get(item_name)
                if store_file and store_file not in name_to_files.get(item_name, []):
                    name_to_files[item_name].append(store_file)

        # ------------------------------------------------------------------
        # Keep only names with more than one distinct file.
        # ------------------------------------------------------------------
        duplicates: Dict[str, DuplicateItemInfo] = {}
        for item_name, files in name_to_files.items():
            unique_files = list(dict.fromkeys(files))  # deduplicate, preserve order
            if len(unique_files) > 1:
                duplicates[item_name] = DuplicateItemInfo(
                    item_name=item_name,
                    file_paths=unique_files,
                )

        return duplicates

    def generate_full_report(self) -> Dict:
        """Generate a comprehensive analysis report"""
        code_references = self.codebase_analyzer.find_all_item_references()
        config_references = self.config_analyzer.analyze_all_configs()
        config_items = self.config_analyzer.get_all_referenced_items()
        all_items = self.item_store.get_all_items()
        
        # Convert code references to serializable format
        serializable_code_references = {}
        for item_name, refs in code_references.items():
            serializable_code_references[item_name] = [
                {
                    'file_path': ref.file_path,
                    'line_number': ref.line_number,
                    'column': ref.column,
                    'context': ref.context,
                    'method_used': ref.method_used
                }
                for ref in refs
            ]
        
        # Convert config references to serializable format
        serializable_config_references = {}
        for item_name, config_refs in config_references.items():
            serializable_config_references[item_name] = [
                {
                    'file_path': config_ref.file_path,
                    'context': config_ref.context,
                    'count': config_ref.count
                }
                for config_ref in config_refs
            ]
        
        # Get detailed missing items info
        missing_items = self.find_missing_items()
        detailed_missing = {}
        
        for item_name, missing_info in missing_items.items():
            detailed_missing[item_name] = {
                'total_references': missing_info.total_references,
                'suggested_matches': [
                    {
                        'item_name': match.item_name,
                        'similarity': round(match.similarity, 3),
                        'match_type': match.match_type
                    }
                    for match in missing_info.suggested_matches
                ],
                'code_references': [
                    {
                        'file_path': ref.file_path,
                        'line_number': ref.line_number,
                        'column': ref.column,
                        'context': ref.context,
                        'method_used': ref.method_used
                    }
                    for ref in missing_info.code_references
                ],
                'config_references': [
                    {
                        'file_path': config_ref.file_path,
                        'context': config_ref.context,
                        'count': config_ref.count
                    }
                    for config_ref in missing_info.config_references
                ]
            }

        # Get duplicate items info
        duplicate_items = self.find_duplicate_items()
        serializable_duplicates = {
            item_name: {
                'count': dup_info.count,
                'file_paths': dup_info.file_paths,
            }
            for item_name, dup_info in duplicate_items.items()
        }
        
        report = {
            'summary': {
                'total_items_in_store': len(all_items),
                'total_code_references': len(code_references),
                'total_config_references': len(config_items),
                'unique_items_in_code': len(code_references),
                'unique_items_in_configs': len(config_items),
                'missing_items_count': len(missing_items),
                'duplicate_items_count': len(duplicate_items),
                'config_files_analyzed': len(set(
                    config_ref.file_path 
                    for config_refs in config_references.values() 
                    for config_ref in config_refs
                ))
            },
            'orphaned_items': self.find_orphaned_items(),
            'missing_items': detailed_missing,
            'duplicate_items': serializable_duplicates,
            'code_references': serializable_code_references,
            'config_references': serializable_config_references,
            'items_in_store': [item.get('name') for item in all_items if item.get('name')],
            'config_patterns': [
                {
                    'directory': str(pattern['directory']),
                    'type': pattern['type'],
                    'params': pattern['params']
                }
                for pattern in self.config_analyzer.config_patterns
            ]
        }
        
        return report


def main():
    """CLI interface for the analyzer"""
    parser = argparse.ArgumentParser(description='Analyze game asset usage')
    parser.add_argument('--code-root', required=True, help='Root directory of the codebase')
    parser.add_argument('--item-store', required=True, help='Item store directory')
    parser.add_argument('--check-item', help='Check usage of a specific item')
    parser.add_argument('--find-orphaned', action='store_true', help='Find orphaned items')
    parser.add_argument('--find-missing', action='store_true', help='Find missing items')
    parser.add_argument('--find-duplicates', action='store_true', help='Find items with duplicate names in the item store')
    parser.add_argument('--full-report', help='Generate full report and save to file')
    
    args = parser.parse_args()
    
    try:
        analyzer = GameAssetAnalyzer(args.code_root, args.item_store)
        
        # CONFIGURE YOUR CONFIG PATTERNS HERE
        # Example configurations - modify these paths for your project:
        
        # Room configs: JSON files where all keys except 'initial_room' contain item lists
        # analyzer.add_config_pattern('./configs/rooms', 'room_configs', ignore_key='initial_room')
        
        # Nested configs: JSON files with nested dictionaries containing 'items' key
        # analyzer.add_config_pattern('./configs/quests', 'nested_items', items_key='items')
        
        # # # Add your actual config patterns here:

        analyzer.add_config_pattern('inventory_items/base_state_manager/houses_configs', 'room_configs', ignore_key='initial_room')

        analyzer.add_config_pattern('inventory_items/items_provider/care_packages_data', 'nested_items', items_key='items')
        if args.check_item:
            report = analyzer.check_item_usage(args.check_item)
            print(f"\nItem: {report.item_name}")
            print(f"Exists in store: {report.exists_in_store}")
            if report.file_path_in_store:
                print(f"Store file: {report.file_path_in_store}")
            print(f"References found: {len(report.references)}")
            
            for ref in report.references:
                if ref.method_used == "config_reference":
                    rel_path = os.path.relpath(ref.file_path, args.code_root)
                    print(f"  {rel_path} - {ref.context}")
                else:
                    rel_path = os.path.relpath(ref.file_path, args.code_root)
                    print(f"  {rel_path}:{ref.line_number} - {ref.method_used}() - {ref.context}")
        
        if args.find_orphaned:
            orphaned = analyzer.find_orphaned_items()
            print(f"\nOrphaned items ({len(orphaned)}):")
            for item in orphaned:
                print(f"  {item}")
        
        if args.find_missing:
            missing_items = analyzer.find_missing_items()
            print(f"\nMissing items ({len(missing_items)}):")
            
            for item_name, missing_info in missing_items.items():
                print(f"\n  {item_name} (referenced {missing_info.total_references} times):")
                
                # Show suggestions
                if missing_info.suggested_matches:
                    print("    💡 Did you mean:")
                    for match in missing_info.suggested_matches[:3]:  # Show top 3 suggestions
                        similarity_percent = int(match.similarity * 100)
                        print(f"      '{match.item_name}' ({similarity_percent}% match, {match.match_type})")
                
                # Show code references
                if missing_info.code_references:
                    print("    📄 Code references:")
                    for ref in missing_info.code_references:
                        rel_path = os.path.relpath(ref.file_path, args.code_root)
                        print(f"      {rel_path}:{ref.line_number} - {ref.method_used}() - {ref.context}")
                
                # Show config references
                if missing_info.config_references:
                    print("    ⚙️  Config references:")
                    for config_ref in missing_info.config_references:
                        rel_path = os.path.relpath(config_ref.file_path, args.code_root)
                        print(f"      {rel_path} - {config_ref.context}")

        if args.find_duplicates:
            duplicate_items = analyzer.find_duplicate_items()
            print(f"\nDuplicate item names in store ({len(duplicate_items)}):")

            if not duplicate_items:
                print("  ✅ No duplicates found.")
            else:
                for item_name, dup_info in sorted(duplicate_items.items()):
                    print(f"\n  ⚠️  '{item_name}' defined in {dup_info.count} files:")
                    for file_path in dup_info.file_paths:
                        rel_path = os.path.relpath(file_path, args.code_root)
                        print(f"      {rel_path}")
        
        if args.full_report:
            report = analyzer.generate_full_report()
            with open(args.full_report, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nFull report saved to {args.full_report}")
            print(f"Analyzed {report['summary']['config_files_analyzed']} config files")
            print(f"Found {report['summary']['unique_items_in_configs']} unique items in configs")
            print(f"Found {report['summary']['missing_items_count']} missing items")
            print(f"Found {report['summary']['duplicate_items_count']} duplicate item names in store")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())


# from main projects root
# python inventory_items/items_provider/items_scanner.py --code-root "." --item-store inventory_items/items_provider/items_data --full-report items_report_details.json


# This will point at any defined items in the code or config files that do not exist in the item store
# Empty lists are fine even if this script higlights them

# python inventory_items/items_provider/items_scanner.py --code-root "." --item-store inventory_items/items_provider/items_data --find-missing

# Find duplicate item names in the store:
# python inventory_items/items_provider/items_scanner.py --code-root "." --item-store inventory_items/items_provider/items_data --find-duplicates