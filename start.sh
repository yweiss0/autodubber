#!/bin/bash
echo "Starting AutoDubber with Docker..."
echo ""
echo "This will:"
echo "- Download and install all dependencies"
echo "- Start the frontend on http://localhost:5173"
echo "- Start the backend API on http://localhost:8000"
echo "- Open your browser to the application"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Start the containers in detached mode
docker-compose up -d --build

# Wait a few seconds for the services to start
echo ""
echo "Waiting for services to start..."
sleep 5

# Open the browser (works on Mac and most Linux distros)
echo "Opening browser..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:5173
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open http://localhost:5173 2>/dev/null || echo "Please open http://localhost:5173 in your browser"
else
    echo "Please open http://localhost:5173 in your browser"
fi

echo ""
echo "AutoDubber is running!"
echo ""
echo "To view logs, run: docker-compose logs -f"
echo "To stop, run: ./stop.sh or press Ctrl+C here"
echo ""

# Keep the script running and follow logs
docker-compose logs -f 