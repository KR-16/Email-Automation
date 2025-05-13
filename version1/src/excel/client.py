"""
Excel Client Module
==================

This module provides functionality to interact with Excel files for storing
and retrieving candidate information and email processing results.
"""

import logging
import pandas as pd
from typing import Dict, List
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORY_COLUMNS = [
    'Initial_Automation',
    'Interview_Automation',
    'Assessment_Automation',
    'Application_Automation',
    'Rejection_Automation',
    'Other_Automation'
]
ALL_COLUMNS = [
    'Name', 'Email',
    'Initial_Automation', 'Interview_Automation', 'Assessment_Automation',
    'Application_Automation', 'Rejection_Automation', 'Other_Automation',
    'Last Updated'
]
CATEGORY_TO_COLUMN = {
    'Initial': 'Initial_Automation',
    'Interview': 'Interview_Automation',
    'Assessment': 'Assessment_Automation',
    'Application': 'Application_Automation',
    'Rejection': 'Rejection_Automation',
    'Other': 'Other_Automation'
}

class ExcelClient:
    def __init__(self, input_file_path: str):
        """
        Initialize Excel client with input file path.
        
        Args:
            input_file_path (str): Path to input Excel file containing candidate information
        """
        self.input_file_path = input_file_path
        self.candidates_df = None
        self.label_counts_df = pd.DataFrame(columns=ALL_COLUMNS)
        self._initialize_candidates_df()
    
    def _initialize_candidates_df(self) -> None:
        """
        Initialize or load DataFrames from input Excel file.
        """
        try:
            # Try to load existing file
            try:
                df = pd.read_excel(self.input_file_path)
                logger.info("Successfully loaded existing Excel file")
            except FileNotFoundError:
                logger.error(f"Input Excel file not found: {self.input_file_path}")
                raise
            except Exception as e:
                logger.error(f"Error loading Excel file: {str(e)}")
                raise
            
            # Ensure required columns exist
            required_cols = ['Name', 'candidateEmail__c', 'candidatePassword__c']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns in Excel file. Required: {required_cols}")
                raise ValueError("Invalid Excel file format")
            
            self.candidates_df = df[required_cols].copy()
            
        except Exception as e:
            logger.error(f"Failed to initialize candidates DataFrame: {str(e)}")
            raise
    
    def get_candidates(self) -> List[Dict]:
        """
        Get list of candidates from Excel file.
        
        Returns:
            List[Dict]: List of candidate dictionaries
        """
        try:
            if self.candidates_df is None or self.candidates_df.empty:
                logger.warning("No candidates found in Excel file")
                return []
            
            return self.candidates_df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Failed to get candidates: {str(e)}")
            raise
    
    def update_label_count(self, candidate: dict, category: str):
        """
        Update label count for a candidate.
        
        Args:
            candidate (dict): Candidate dictionary
            category (str): Category to update
        """
        try:
            email = candidate.get('Email') or candidate.get('candidateEmail__c')
            name = candidate.get('Name')
            excel_column = CATEGORY_TO_COLUMN.get(category, 'Other_Automation')
            idx = self.label_counts_df.index[self.label_counts_df['Email'] == email].tolist()
            if not idx:
                # Add new candidate row if not present
                new_row = {col: 0 for col in CATEGORY_COLUMNS}
                new_row.update({'Name': name, 'Email': email, 'Last Updated': None})
                self.label_counts_df = pd.concat([
                    self.label_counts_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)
                idx = self.label_counts_df.index[self.label_counts_df['Email'] == email].tolist()
            row_idx = idx[0]
            self.label_counts_df.at[row_idx, excel_column] += 1
            self.label_counts_df.at[row_idx, 'Last Updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Failed to update label count for candidate {candidate}: {str(e)}")
            raise
    
    def save_results(self, output_dir: str = None) -> str:
        """
        Save label counts to a new Excel file.
        
        Args:
            output_dir (str, optional): Directory to save the output file. Defaults to same directory as input file.
            
        Returns:
            str: Path to the saved output file
        """
        try:
            if self.label_counts_df is None or self.label_counts_df.empty:
                logger.warning("No label counts to save")
                return None
            
            # Determine output directory
            if output_dir is None:
                output_dir = os.path.dirname(self.input_file_path)
            
            # Create output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"candidate_label_counts_{timestamp}.xlsx"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save to Excel file
            self.label_counts_df.to_excel(output_path, index=False)
            
            logger.info(f"Saved candidate label counts to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
            raise 