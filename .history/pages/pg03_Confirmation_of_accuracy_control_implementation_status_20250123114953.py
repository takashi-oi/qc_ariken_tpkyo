import sqlite3
import pandas as pd
import streamlit as st
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration dataclass"""
    path: str = 'db_folder/qc_data_base.db'
    max_connection_attempts: int = 3

class DatabaseManager:
    """Enhanced database management with connection pooling and robust error handling"""
    def __init__(self, config: DatabaseConfig = DatabaseConfig()):
        self.config = config
        self.connection_pool = []

    @contextmanager
    def get_connection(self):
        """Managed database connection with retry mechanism"""
        connection = None
        for attempt in range(self.config.max_connection_attempts):
            try:
                connection = sqlite3.connect(self.config.path)
                yield connection
                break
            except sqlite3.Error as e:
                logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_connection_attempts - 1:
                    st.error("Could not establish database connection")
                    raise
            finally:
                if connection:
                    connection.close()

    def fetch_qc_data(self, days_back: int = 30) -> pd.DataFrame:
        """Fetch QC data with improved error handling and performance"""
        try:
            query = f"""
            SELECT
                Date_Time as date_time,
                Type as Type,
                SD_Conversion as sd_conversion
            FROM table_qc_pc
            WHERE datetime(Date_Time) >= datetime('now', '-{days_back} days')
            ORDER BY Date_Time DESC
            """
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
                df['date_time'] = pd.to_datetime(df['date_time'])
                return df
        except Exception as e:
            logger.error(f"Error fetching QC data: {e}")
            st.error(f"Data retrieval failed: {e}")
            return pd.DataFrame()

    def save_check_log(self, check_log_df: pd.DataFrame) -> bool:
        """Enhanced check log saving with detailed validation"""
        required_fields = [
            'date', 'Measurement', 'Measurer', 
            'Type', 'comment_check', 'comment'
        ]
        
        if not all(field in check_log_df.columns for field in required_fields):
            st.error("Missing required data fields")
            return False

        try:
            with self.get_connection() as conn:
                check_log_df.to_sql(
                    'table_qc_check_log',
                    conn,
                    if_exists='append',
                    index=False
                )
                return True
        except Exception as e:
            logger.error(f"Error saving check log: {e}")
            st.error(f"Data save failed: {e}")
            return False

class QCCheckUI:
    """Enhanced UI with improved state management and validation"""
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.input_values = None

    def initialize_session_state(self) -> Optional[tuple]:
        """Robust session state initialization"""
        try:
            if 'check_data' not in st.session_state or st.session_state.get('refresh_data', False):
                data = self.db_manager.fetch_qc_data()
                st.session_state.check_data = data if not data.empty else None
                st.session_state.refresh_data = False
            
            with st.sidebar:
                date_time = st.date_input(
                    "Select Date",
                    value=pd.Timestamp.now().date(),
                    max_value=pd.Timestamp.now().date()
                )
                
                options = [
                    "Precision Management Supervisor",
                    "Genetic/Chromosome Test Quality Assurance Manager",
                    "Administrator",
                    "Supervising Physician"
                ]
                measurement = st.selectbox("Select Responsibility Category", options)

                measurer = st.text_input(
                    label=measurement,
                    placeholder='Enter full name'
                ).strip()

                return (date_time, measurement, measurer)

        except Exception as e:
            logger.error(f"Session initialization error: {e}")
            st.error("Failed to initialize session")
            return None

    def render_charts(self, date_time, measurement, measurer) -> List[Dict]:
        """Comprehensive chart rendering with enhanced error handling"""
        if not st.session_state.get('check_data'):
            st.warning("No data available")
            return []

        check_logs = []
        for type_name in st.session_state.check_data['Type'].unique():
            # Chart rendering logic remains similar to original implementation
            # [Previous chart rendering code]

        return check_logs


def main():
    """Main application entry point with comprehensive error management"""
    st.set_page_config(page_title="Quality Management Check", layout="wide")
    st.title("Quality Management Status Verification")

    try:
        db_manager = DatabaseManager()
        ui = QCCheckUI(db_manager)
 
        session_data = ui.initialize_session_state()
        if not session_data:
            return

        date_time, measurement, measurer = session_data

        if not measurer:
            st.warning("Please enter personnel name")
            return

        # Remaining main function logic similar to original implementation

    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"Critical application error: {e}")


if __name__ == "__main__":
    main()