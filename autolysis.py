# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "numpy",
#   "pandas",
#   "requests",
#   "python-dotenv",
#   "seaborn",
#   "matplotlib",
#   "tenacity"
# ]
# ///

import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import logging
import os
import sys
import requests
from tenacity import retry, stop_after_attempt
from dotenv import load_dotenv
import base64

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load token from .env file
AIPROXY_TOKEN = os.environ["AIPROXY_TOKEN"]

if(not AIPROXY_TOKEN):
    logging.error("Error: Couldn't read AI Proxy Token")
    sys.exit(1)

LLM_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

LLM_HEADER = {"Authorization": f"Bearer {AIPROXY_TOKEN}"}


# Capture basic information regarding the dataset like dimensions, column names, datatypes and null value count
def capture_info(dataframe):
    """
    Capture information on the dataset like dimensions, column names, datatypes and null value count

    Args:
        dataframe (pandas.DataFrame): Dataframe to be summarized

    Returns:
        dict : Python dictionary containing all summarized information pertaining to the dataset
    """
    
    info_dict = {
        "num_rows": len(dataframe),
        "num_columns": len(dataframe.columns),
        "columns": []
    }
    
    for column in dataframe.columns:
        col_data = {
            "name": column,
            "dtype": str(dataframe[column].dtype),
            "non_null_count": int(dataframe[column].notnull().sum())
        }
        info_dict["columns"].append(col_data)
        
    return info_dict


# Read csv file and generate summary
def analyze_csv(file_path):
    """
    Reads a CSV file, generates a summary of the data, and returns the data and summary.

    Args:
        file_path (str): The path to the CSV file to be analyzed.

    Returns:
        data (Pandas.DataFrame): The loaded dataframe from the CSV file.
        summary (dict): A dictionary containing metadata about the dataframe, including:
            - 'columns': List of column names.
            - 'data_types': Data types of the columns.
            - 'non_null_count': Count of non-null values per column.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        pd.errors.ParserError: If the CSV file cannot be parsed.
    """
    
    logging.info(f"Loading data from {file_path}...")
    
    # Try loading the CSV with multiple encodings for compatibility
    try:
        data = pd.read_csv(file_path, encoding="ISO-8859-1")
    except UnicodeDecodeError:
        logging.warning("ISO-8859-1 encoding failed. Retrying with UTF-8.")
        data = pd.read_csv(file_path, encoding="utf-8")
    except FileNotFoundError:
        logging.error("The specified file was not found.")
        raise
    except pd.errors.ParserError as e:
        logging.error("Error parsing the CSV file: %s", e)
        raise
    
    # Ensure data is JSON serializable
    data = data.apply(lambda x: int(x) if isinstance(x, np.int64) else x)
    
    # Summary statistics and basic info
    summary = {
        "columns": list(data.columns),
        "info": capture_info(data)
    }
    
    logging.info("Data loaded and summarized successfully.")
    
    return data, summary


# Call LLM API
def make_llm_api_call(sys_prompt, user_prompt, image_encoded_dict = None):
    """
    Makes API calls to the OpenAI LLM API

    Args:
        sys_prompt (str): System prompt to be passed to the LLM
        user_prompt (str): User prompt to be passed to the LLM
        image_encoded_dict (dict) [optional]: Dictionary containing image details for LLM visualization

    Raises:
        ValueError: Raise error in case of an unexpected API response format
        RequestException: Raise an HTTPError for bad responses (4xx and 5xx)
        Exception: If the LLM API call fails, the exception is propagated

    Returns:
        str: LLM-generated API response
    """
    
    messages = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": [
                        {
                            "type": "text", 
                            "text": user_prompt
                        },
                    ]}
                ]
    
    if(image_encoded_dict is not None):
        messages[1]["content"].append(image_encoded_dict)
        
    
    try:
        response = requests.post(
            url=LLM_URL,
            headers=LLM_HEADER,
            json={
                "model": "gpt-4o-mini",
                "messages": messages
            }
        )
        
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        
        result = response.json()
        
        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"]
        else:
            logging.error("Invalid response format from LLM API: %s", result)
            raise ValueError("Unexpected response format from LLM API.")
    except requests.RequestException as e:
        logging.error("Network error while communicating with LLM API: %s", e)
        raise
    except Exception as e:
        logging.error("Unexpected error during LLM API call: %s", e)
        raise

    
# Using an LLM to generate python code to create a correlation matrix heatmap
@retry(reraise=True, stop=stop_after_attempt(5))
def generate_corr_matrix(df):
    """
    Generates a Correlation Heatmap for the input dataframe using LLM-generated code 
    
    Args:
        df (pandas.DataFrame): Dataframe to analyse. The df is analysed using an LLM-generated code.

    Raises:
        Exception: If the LLM API call fails or if the generated code encounters any errors 
            during execution, the exception is propagated.
    """
    logging.info("Generating correlation matrix heatmap...")
        
    sys_prompt = ("You are to generate a python code for the given task. Only output the code and nothing else." 
        "The code is run in an interperter so do not add the \"python\" command in the front." 
        "Don't try to visualize the graph as the code is not running in a jupyter notebook."
    )
    
    user_prompt =  (
        f"Generate Python code to generate a correlation heatmap for a pandas dataframe named df using the seaborn library "
        f"and save it in the current folder as a 512x512 png image named \"correlation_heatmap.png\". "
        f"Make sure to consider only numeric data for calculations. Ignore strings and other datatypes. Just save the file."
    )
    
    try:
        corr_map_code = make_llm_api_call(sys_prompt, user_prompt)
        exec(corr_map_code)
        
    except Exception as e:
        logging.error("Error executing generated code: %s", e)
        raise
    

# Generate box-plots for all numerical columns
def generate_box_plots(df):
    """
    Generates Box plots for all numerical columns for an input dataframe and store them in a location

    Args:
        df (pandas.DataFrame): Dataframe to analyse
    """
    
    logging.info("Generating box plots for numerical columns...")

    # Identify numerical columns
    numerical_cols = df.select_dtypes(include=['number']).columns

    # Check if there are numerical columns
    if len(numerical_cols) > 0:
        # Set up the figure size and grid
        plt.figure(figsize=(15, len(numerical_cols) * 3))
        
        # Generate box plots
        for i, col in enumerate(numerical_cols, start=1):
            plt.subplot(len(numerical_cols), 1, i)
            plt.boxplot(df[col].dropna(), vert=False, patch_artist=True, boxprops=dict(facecolor='skyblue'))
            plt.title(f"Box Plot: {col}", fontsize=12)
            plt.xlabel(col, fontsize=10)
            plt.grid(axis='x', linestyle='--', alpha=0.7)

        # Save the plot to a file
        output_path = "./box_plots.png"
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
    
    
# Generate histograms for all columns    
def generate_histograms(df):
    """
    Generates histograms for all columns for an input dataframe and store them in a location

    Args:
        df (pandas.DataFrame): Dataframe to analyse
    """
    
    logging.info("Generating histograms...")
    
    # Select numerical and categorical columns
    numerical_columns = df.select_dtypes(include=['number']).columns
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns

    # Initialize a list to store columns with more than 15 categories
    ignored_columns = []
    plot_columns = []

    # Separate categorical columns based on the number of unique categories
    for col in categorical_columns:
        unique_categories = df[col].nunique()
        if unique_categories > 15:
            ignored_columns.append(col)
        else:
            plot_columns.append(col)

    # Combine numerical and filtered categorical columns for plotting
    all_columns = list(numerical_columns) + plot_columns

    # Set up the grid layout for the plots (3 columns)
    n_cols = 3
    n_rows = -(-len(all_columns) // n_cols)  # Calculate rows needed, ceiling division

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
    axes = axes.flatten()  # Flatten to iterate easily

    # Plot the data
    for i, col in enumerate(all_columns):
        if col in numerical_columns:
            # Plot histogram for numerical columns
            sns.histplot(df[col], kde=True, ax=axes[i], bins=30, color='blue')
            axes[i].set_title(f'Histogram of {col}')
        else:
            # Plot count plot for categorical columns
            sns.countplot(data=df, x=col, order=df[col].value_counts().index, ax=axes[i])
            axes[i].set_title(f'Distribution of {col}')
            axes[i].tick_params(axis='x', rotation=45)

    # Turn off unused subplots
    for i in range(len(all_columns), len(axes)):
        axes[i].axis('off')

    # Adjust layout and save the figure
    plt.tight_layout()
    plt.savefig("histograms.png", dpi=300)
        
        
# Generate insights with the help of an LLM using the summary
@retry(reraise=True, stop=stop_after_attempt(3))
def ask_llm_for_insights(summary):
    """
    Makes API calls to the OpenAI LLM API to generate data insights using the data summary and correlation heatmap as references.
    The input *.png images are encoded in base64 format to pass the image ure in the API accordingly.

    Args:
        summary (dict): A dictionary containing metadata about the dataframe, including:
            - 'columns': List of column names.
            - 'data_types': Data types of the columns.
            - 'non_null_count': Count of non-null values per column. 

    Returns:
        str: LLM-generated insights. The insights are generated in a markup format for display in a *.md file.
    """
    
    logging.info("Generating insights...")

    sys_prompt = ("Analyze the following dataset summary and provide key insights and actionable recommendations."
        "Use the correlation heatmap provided with the prompt" 
        "Write the output in markup format so that it can be properly viewed in a .md file"
    )
    
    with open('correlation_heatmap.png', 'rb') as image_file:
        image_data = image_file.read()

    # Encode the image data to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')

    image_details = {
                        "type": "image_url", 
                        "image_url": { 
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "low"
                        }
                    }

    return make_llm_api_call(sys_prompt, str(summary), image_details)        
        
        
# Output all insights into a readme file
def create_readme(insights):
    """
    Generates a Markdown file with insights and saves it in the specified directory.
    
    Args:
        insights (str): The content to be written to the README.md file. 
                        It should be a string formatted as Markdown.
        output_dir (str): The directory where the README.md file will be created.
                        If the directory does not exist, it will be created.
    
    Raises:
        Exception: For any errors during file writing.
    """

    try:
        # Construct the output file path
        output_file = "./README.md"
        
        clean_insights = insights.strip("```markdown\n")

        # Write insights to the file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(clean_insights)
        
        logging.info(f"README.md created successfully at {output_file}")
    except Exception as e:
        logging.error(f"Failed to create README.md: {e}")
        raise
    
    
# Main function call 
if __name__ == "__main__":
    # Checking function call arguments
    if len(sys.argv) != 2:
        logging.info("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)
        
    file_name = sys.argv[1]
    
    df, summary = analyze_csv(file_name)
        
    file_name_without_extension = os.path.splitext(file_name)[0]
        
    # Generate correlation matrix
    generate_corr_matrix(df)
    
    generate_box_plots(df)
    
    generate_histograms(df)
        
    # Generating insights
    insights = ask_llm_for_insights(summary)
    
    create_readme(insights)
    
    logging.info("Analysis successful")
