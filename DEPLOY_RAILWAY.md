# Railway deployment
1. Create a new GitHub repository in your own account and push these files to its `main` branch.
2. In Railway, create a project and choose Deploy from GitHub Repo.
3. Select this repository. Railway builds the included Dockerfile.
4. Add a persistent volume mounted at `/data`.
5. Wait for `/health` to return `{"status":"ok"}` and open the Railway public domain.
6. Submit a topic in the browser UI. The MP4 download appears after the worker verifies the output.
Hosting can incur charges; review billing before enabling paid usage. The user's own computer/GPU is not involved.
