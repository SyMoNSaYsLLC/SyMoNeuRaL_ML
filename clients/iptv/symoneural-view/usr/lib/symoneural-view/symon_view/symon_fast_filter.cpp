#include <vector>
#include <string>
#include <algorithm>
#include <cstring>
#include <cctype>
#include <iostream>

// Lowercase helper
static std::string to_lower(const std::string& s) {
    std::string out = s;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char c){ return std::tolower(c); });
    return out;
}

/**
 * Filter items by query string.
 * Returns the number of matches, fills indices array.
 */
extern "C" {
    int filter_items(const char** names, const char** groups, int n, const char* query, int* indices, int max_results) {
        if (!names || !groups || !query || !indices || n <= 0 || max_results <= 0) {
            std::cerr << "Invalid arguments to filter_items\n";
            return 0;
        }
        int count = 0;
        std::string q = to_lower(query);
        for (int i = 0; i < n; ++i) {
            std::string name = to_lower(names[i] ? names[i] : "");
            std::string group = to_lower(groups[i] ? groups[i] : "");
            if (name.find(q) != std::string::npos || group.find(q) != std::string::npos) {
                indices[count++] = i;
                if (count >= max_results) break;
            }
        }
        return count;
    }
}