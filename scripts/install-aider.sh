#!/bin/bash
# Install Aider with Gemini API integration

echo "🚀 Installing Aider for AI-powered coding..."
echo ""

# Install pipx via apt (requires sudo)
echo "📦 Installing pipx..."
sudo apt update && sudo apt install -y pipx

# Ensure pipx is in PATH
pipx ensurepath

# Install aider-chat
echo ""
echo "📦 Installing aider-chat..."
pipx install aider-chat

# Get Gemini API key from Secret Manager
echo ""
echo "🔑 Fetching Gemini API key from Google Secret Manager..."
GEMINI_KEY=$(gcloud secrets versions access latest --secret="GOOGLE_AI_API_KEY" --project=regal-scholar-453620-r7)

# Add to .bashrc for persistence
echo ""
echo "💾 Adding Gemini API key to ~/.bashrc..."
if ! grep -q "GOOGLE_API_KEY" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Gemini API for Aider" >> ~/.bashrc
    echo "export GOOGLE_API_KEY=\"$GEMINI_KEY\"" >> ~/.bashrc
fi

# Export for current session
export GOOGLE_API_KEY="$GEMINI_KEY"

echo ""
echo "✅ Installation complete!"
echo ""
echo "📚 Quick Start Guide:"
echo "-------------------"
echo "1. Start a new terminal OR run: source ~/.bashrc"
echo ""
echo "2. Basic usage:"
echo "   aider --model gemini/gemini-2.0-flash-exp"
echo ""
echo "3. Work with specific files:"
echo "   aider main.py utils.py"
echo ""
echo "4. Get help:"
echo "   aider --help"
echo ""
echo "5. Common commands inside Aider:"
echo "   /add <file>     - Add file to chat"
echo "   /drop <file>    - Remove file from chat"
echo "   /commit         - Commit changes"
echo "   /diff           - Show changes"
echo "   /undo           - Undo last change"
echo "   /help           - Show all commands"
echo "   /exit           - Quit Aider"
echo ""
echo "🎯 Example Strategic Session:"
echo "   aider --model gemini/gemini-2.0-flash-exp cloud-run-backend/main.py"
echo "   Then ask: 'What architectural improvements would you suggest?'"
echo ""
echo "💡 Tip: Use Aider for strategic planning and architecture"
echo "   Use Cursor (me!) for day-to-day implementation"
echo ""


