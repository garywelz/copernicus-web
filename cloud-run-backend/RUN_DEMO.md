# How to Run the Interactive Demo

## Option 1: Run the Shell Script (Easiest)

Just run this single command:

```bash
/home/gdubs/copernicus-web-public/cloud-run-backend/run_demo.sh
```

Or if you're already in the project directory:

```bash
./cloud-run-backend/run_demo.sh
```

## Option 2: Type Commands Manually

If pasting doesn't work, type these commands one at a time:

1. Navigate to the directory:
   ```
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   ```

2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

3. Run the demo:
   ```
   python3 scripts/interactive_vector_search.py
   ```

## Option 3: Use the Quick Search Instead

If you just want to try a quick search without the interactive demo:

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/quick_search.py "DNA replication"
```

## Troubleshooting

If you get "command not found" or "permission denied":
- Make sure you're in the right directory
- Try: `bash /home/gdubs/copernicus-web-public/cloud-run-backend/run_demo.sh`
- Or: `sh /home/gdubs/copernicus-web-public/cloud-run-backend/run_demo.sh`

