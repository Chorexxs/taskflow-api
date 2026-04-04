# TaskFlow Frontend

React + Vite + Tailwind CSS frontend for TaskFlow API.

## Getting Started

```bash
# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# Run development server
npm run dev
```

## Features

- Authentication (Login/Register)
- Teams management
- Projects with Kanban board
- Drag and drop tasks
- Comments
- Notifications with polling
- Dark mode
- Filters and search

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- React Router v6
- TanStack Query
- @dnd-kit for drag and drop
- React Hot Toast

## Environment Variables

```
VITE_API_URL=http://localhost:8000
```

## Build

```bash
npm run build
```

## Demo

Live demo: https://taskflow-demo.vercel.app

Test account:
- Email: demo@taskflow.app
- Password: demopass123
