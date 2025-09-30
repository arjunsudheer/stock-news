cd $HOME/code/personal_projects/stock-news
source venv/bin/activate

# Clear any existing logs or output files
rm -f output.log
rm -f analysis_report.txt

# Run the script
python3 main.py