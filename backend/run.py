import uvicorn

if __name__ == "__main__":
    print("Starting AutoDubber API server...")
    # Configure Uvicorn to handle larger file uploads (2GB)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        limit_concurrency=5,  # Limit concurrent connections during large uploads
        timeout_keep_alive=300,  # Increased keep-alive timeout for large uploads
        limit_max_requests=10,  # Limit max requests to prevent memory issues
    )
