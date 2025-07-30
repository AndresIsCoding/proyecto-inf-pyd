import pandas as pd
import yfinance as yf
import numpy as np
import warnings
import logging
import time
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# --- Configuration ---
# Configure logging to see output in Docker logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress specific pandas warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="S&P 500 Data Loader",
    description="A microservice to download and serve S&P 500 stock data.",
)

# --- Global State ---
# Use a global variable to hold the main dataframe. Initialize to None.
df_global: pd.DataFrame | None = None

# --- Core Data Loading Logic ---
def load_sp500_data():
    """
    Fetches and processes S&P 500 stock data from Yahoo Finance.

    This function is designed to be robust by:
    1.  Downloading data in small, manageable chunks.
    2.  Pausing between chunks to avoid API rate-limiting.
    3.  Handling errors for individual chunks without crashing.
    """
    global df_global
    
    try:
        logger.info("--- Starting S&P 500 data download process ---")

        # 1. Get the list of S&P 500 company symbols
        logger.info("Fetching S&P 500 company list from Wikipedia...")
        sp500_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_df = pd.read_html(sp500_url)[0]
        sp500_df['Symbol'] = sp500_df['Symbol'].str.replace('.', '-', regex=False)
        symbol_list = sp500_df['Symbol'].unique().tolist()
        
        # Remove known problematic symbols that yfinance struggles with
        problematic_symbols = ['BF.B', 'BRK.B', 'GEV', 'SOLV', 'VLTO']
        symbol_list = [s for s in symbol_list if s not in problematic_symbols]
        
        logger.info(f"Successfully fetched {len(symbol_list)} symbols.")

        # 2. Set up download parameters
        start_date = "2024-01-01"
        end_date = "2024-12-31"
        all_data = []
        
        # CRITICAL: Use a small chunk size and a delay to avoid being rate-limited
        chunk_size = 5
        delay_between_chunks = 2  # seconds

        # 3. Download data in chunks
        num_chunks = (len(symbol_list) + chunk_size - 1) // chunk_size
        for i in range(0, len(symbol_list), chunk_size):
            chunk = symbol_list[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            logger.info(f"Processing chunk {chunk_num}/{num_chunks}: {chunk}")

            try:
                df_chunk = yf.download(
                    tickers=chunk,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    auto_adjust=False,
                    threads=False  # CRITICAL: Disable threading
                )

                if not df_chunk.empty:
                    # Normalize the data structure regardless of single or multiple tickers
                    df_chunk = df_chunk.reset_index()
                    
                    if len(chunk) > 1:
                        # Multiple tickers: columns are MultiIndex (metric, ticker)
                        # Stack to get ticker as a column
                        df_chunk = df_chunk.set_index('Date').stack(level=1).reset_index()
                        df_chunk.columns.name = None  # Remove the column name
                        df_chunk = df_chunk.rename(columns={'Date': 'date', 'level_1': 'ticker'})
                    else:
                        # Single ticker: columns are just the metrics
                        df_chunk['ticker'] = chunk[0]
                        df_chunk = df_chunk.rename(columns={'Date': 'date'})

                    # Standardize column names to lowercase
                    df_chunk.columns = [col.lower() if col != 'ticker' else col for col in df_chunk.columns]
                    
                    # Debug: Print column names and shape for troubleshooting
                    logger.info(f"Chunk {chunk_num} columns: {list(df_chunk.columns)}")
                    logger.info(f"Chunk {chunk_num} shape: {df_chunk.shape}")
                    
                    all_data.append(df_chunk)
                    logger.info(f"✓ Successfully downloaded data for chunk {chunk_num}")
                else:
                    logger.warning(f"✗ No data returned for chunk {chunk_num}: {chunk}")

            except Exception as e:
                logger.error(f"✗ FAILED to download chunk {chunk_num} ({chunk}): {e}")

            # CRITICAL: Pause between requests
            if chunk_num < num_chunks:
                logger.info(f"Pausing for {delay_between_chunks} seconds...")
                time.sleep(delay_between_chunks)

        # 4. Consolidate and clean the final DataFrame
        if all_data:
            logger.info("Consolidating all downloaded data...")
            df_temp = pd.concat(all_data, ignore_index=True)
            
            # Debug: Print consolidated DataFrame info
            logger.info(f"Consolidated DataFrame columns: {list(df_temp.columns)}")
            logger.info(f"Consolidated DataFrame shape: {df_temp.shape}")
            
            # Check which required columns actually exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            existing_cols = [col for col in required_cols if col in df_temp.columns]
            missing_cols = [col for col in required_cols if col not in df_temp.columns]
            
            if missing_cols:
                logger.warning(f"Missing expected columns: {missing_cols}")
                logger.info(f"Available columns: {list(df_temp.columns)}")
            
            # Only drop NaN for columns that actually exist
            if existing_cols:
                df_temp.dropna(subset=existing_cols, inplace=True)
                logger.info(f"Dropped NaN values for columns: {existing_cols}")
            
            # Ensure date column is properly formatted
            if 'date' in df_temp.columns:
                df_temp['date'] = pd.to_datetime(df_temp['date']).dt.strftime('%Y-%m-%d')
            
            # Sort for consistency
            sort_cols = ['ticker', 'date'] if 'ticker' in df_temp.columns and 'date' in df_temp.columns else ['ticker']
            if sort_cols[0] in df_temp.columns:
                df_temp = df_temp.sort_values(by=sort_cols).reset_index(drop=True)

            # Assign to the global dataframe
            df_global = df_temp
            logger.info(f"--- ✓ Data loading complete! ---")
            logger.info(f"Total records loaded: {len(df_global)}")
            if 'ticker' in df_global.columns:
                logger.info(f"Unique tickers loaded: {df_global['ticker'].nunique()}")
            logger.info(f"Final DataFrame columns: {list(df_global.columns)}")
        else:
            logger.error("No data was successfully downloaded after all attempts.")
            df_global = None

    except Exception as e:
        logger.critical(f"A critical error occurred during the data loading process: {e}")
        # Add more detailed error information
        import traceback
        logger.critical(f"Traceback: {traceback.format_exc()}")
        df_global = None

# --- FastAPI Events ---
@app.on_event("startup")
async def startup_event():
    """
    This function is called by FastAPI when the application starts.
    It triggers the data loading process.
    """
    logger.info("Application startup: Triggering data load.")
    load_sp500_data()

# --- API Endpoints ---
@app.get("/")
def read_root():
    """Root endpoint providing service status."""
    return {"message": "S&P 500 Data Loader is running."}

@app.get("/health")
def health_check():
    """Health check endpoint to verify service status."""
    if df_global is not None:
        return {"status": "healthy", "data_loaded": True, "records": len(df_global)}
    else:
        return {"status": "unhealthy", "data_loaded": False, "message": "Data failed to load on startup."}

@app.get("/dataset")
def get_dataset():
    """Returns the entire S&P 500 dataset as JSON."""
    if df_global is None:
        return JSONResponse(
            status_code=503, # Service Unavailable
            content={"error": "Dataset not available. Failed to load during startup."}
        )
    
    logger.info(f"Serving dataset with {len(df_global)} records.")
    # Convert dataframe to a list of dictionaries for JSON response
    return JSONResponse(content=df_global.to_dict(orient="records"))

@app.get("/reload")
def reload_dataset():
    """Manually triggers a reload of the dataset."""
    logger.info("Manual reload requested.")
    load_sp500_data()
    if df_global is not None:
        return {"message": "Dataset reloaded successfully.", "records": len(df_global)}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to reload dataset."})