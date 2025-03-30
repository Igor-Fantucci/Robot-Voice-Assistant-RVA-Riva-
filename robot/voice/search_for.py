#!/usr/bin/env python3

import sys
import webbrowser

# Gets the search term from the argument
search_term = sys.argv[1]

# Google search URL (or another search engine)
search_url = f"https://www.google.com/search?q={search_term}"

# Opens Firefox with the search URL
webbrowser.get('firefox').open(search_url)
