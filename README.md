# BB – To-Do List App

A lightweight, dependency-free to-do list that runs entirely in the browser.

## Features

- Add, complete/uncomplete, and delete tasks
- Filter by All / Active / Completed
- Clear all completed tasks at once
- Items are persisted in **browser local storage** – they survive page reloads

## Running locally

No build step required. Just open `index.html` in any modern browser:

```bash
# macOS
open index.html

# Linux
xdg-open index.html

# Or serve it with any static file server, e.g.:
npx serve .
```

## Files

| File | Purpose |
|------|---------|
| `index.html` | App markup + JavaScript logic |
| `style.css` | Styles |
| `README.md` | This file |
