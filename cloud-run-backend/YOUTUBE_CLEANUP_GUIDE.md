# YouTube Playlist Cleanup Guide

## Current Status
- **RSS Feed**: 73 unique episodes (source of truth)
- **YouTube Playlist**: 111 videos
- **Target**: 73 videos (exactly matching RSS feed)
- **To Remove**: 38 videos

## Valid Episodes (Should be in YouTube)

These 73 GUIDs are the ONLY episodes that should be in your YouTube playlist:

1. ever-compsci-250034 - Swarm Intelligence Evolved: Collective AI Systems...
2. ever-math-250043 - Decoding Reality: How Random Matrix Theory...
3. ever-compsci-250033 - Brain-Inspired Revolution: Unveiling the Potential...
4. ever-phys-250045 - Unlocking the Secrets of Topological Phases...
5. ever-phys-250044 - Quantum Sensing Revolution: Unlocking New Realities...
6. ever-math-250042 - Revolutionizing Optimization: Unveiling Gradient-Free...
7. ever-math-250041 - Unveiling Hidden Structures: How Topological Data...
8. ever-compsci-250032 - Graph Neural Networks: Revolutionizing Data Analysis...
9. ever-bio-250043 - Bio-Inspired Catalysis: Unlocking Nature's Secrets...
10. ever-chem-250022 - Supramolecular Self-Assembly: Building the Future...
11. ever-bio-250042 - Revolutionizing Cancer Immunotherapy: AI, Nanotechnology...
12. news-bio-28032025 - Biology News
13. news-chem-28032025 - Chemistry News
14. news-compsci-28032025 - CompSci News
15. news-math-28032025 - Math News
16. news-phys-28032025 - Phys News
17. ever-bio-250007 - CRISPR Epigenome
18. ever-bio-250014 - Minimal Cells
19. ever-bio-250016 - Neural Optogenetics
20. ever-bio-250018 - Organoids
21. ever-bio-250020 - Spatial Biology
22. ever-bio-250028 - Synthetic Biology
23. ever-bio-250029 - Cell Division Mitosis
24. ever-bio-250030 - Cellular Mitosis Process
25. ever-bio-250031 - Plant Science Photosynthesis
26. ever-chem-250002 - Catalysis Revolution
27. ever-chem-250005 - Green Chemistry
28. ever-chem-250015 - Molecular Machines
29. ever-chem-250016 - Chemical Bonds Molecules
30. ever-compsci-250008 - Edge Computing
31. ever-compsci-250017 - Neuromorphic Computing
32. ever-compsci-250024 - Artificial General Intelligence
33. ever-compsci-250025 - Decomposable Flow Matching
34. ever-compsci-250026 - Machine Learning Basics
35. ever-compsci-250027 - Test Prompt
36. ever-math-250009 - Math Logic 2024
37. ever-math-250011 - Godel's Incompleteness Theorem
38. ever-math-250029 - Poincare Conjecture
39. ever-math-250031 - Independence Results
40. ever-math-250032 - Calculus Derivatives Basic
41. ever-math-250033 - New Approach to Prime Gap Distributions
42. ever-phys-250019 - Quantum Machine Learning
43. ever-phys-250021 - String Theory
44. ever-phys-250022 - Higgs Boson
45. ever-phys-250026 - Quantum Entanglement
46. ever-phys-250027 - Quantum Cryptography
47. ever-phys-250030 - Quantum Batteries
48. ever-phys-250031 - Quantum Computing Intro
49. ever-compsci-250030 - Quantum AI: Automating Labs and Simulating Reality
50. ever-phys-250034 - 3I/ATLAS: Unveiling the Secrets of Interstellar...
51. ever-math-250036 - Mathematics Meets Biology: Unlocking New Frontiers...
52. ever-math-250035 - Data-Driven Healthcare: Redefining 21st Century...
53. ever-bio-250036 - Unlocking the Lac Operon: From Bacterial Metabolism...
54. ever-chem-250020 - Carbon's Unfolding Mysteries: From Crystal Growth...
55. ever-phys-250040 - Quantum Gravity: Bridging the Divide with Ancient...
56. ever-chem-250017 - Copernicus AI: Frontiers of Science - AI-Designed...
57. ever-bio-250041 - How Epigenetic Modifications are Inherited
58. ever-phys-250041 - Unlocking the Secrets of Plasma: New Insights...
59. ever-math-250040 - The Vectorization of Thought: How Category Theory...
60. ever-math-250037 - Unraveling the Poincaré Conjecture: A Glimpse...
61. ever-phys-250042 - Quantum Sensing Revolution: Unveiling Hidden Realities...
62. ever-compsci-250031 - Federated Learning: Revolutionizing AI Training...
63. ever-bio-250040 - Revolutionizing COVID-19 Treatment: Emerging Strategies...
64. ever-math-250038 - Unveiling the Frontiers of Arithmetic: From Peano...
65. ever-chem-250019 - Silicon's Surprising Versatility: From Cosmetics...
66. ever-phys-250043 - Quantum Computing chip advances
67. ever-bio-250034 - Lac Operon Reimagined: Boolean Networks and the Future...
68. ever-compsci-250029 - Quantum Leap: Decoding Breakthroughs in Fault-Tolerant...
69. ever-chem-250018 - Silicon Compounds: Revolutionizing Batteries, Sensors...
70. ever-phys-250038 - Quantum Error Correction: Paving the Way for Fault...
71. ever-bio-250039 - Beyond Dopamine: Exploring New Frontiers in Parkinson's...
72. ever-bio-250038 - E. Coli: From Detection to Genome Editing – A Revolutionary...
73. ever-bio-250037 - Yeast Cells: Unlocking Secrets of Immunity, Aging...

## How to Identify Duplicates

### Method 1: Check Video Descriptions
- YouTube videos created from RSS feeds typically include the GUID in the description
- Look for the GUID format: `ever-XXX-XXXXXX` or `news-XXX-XXXXXX`
- If you find 2+ videos with the same GUID, remove duplicates (keep the newest)

### Method 2: Compare Titles
- Look for videos with identical or very similar titles
- Common duplicate patterns:
  - Same title, different publication dates
  - Similar titles (e.g., "Quantum Computing" vs "Quantum Computing chip advances")
  - Videos you already removed due to broken thumbnails

### Method 3: Sort by Date
- In YouTube playlist editor, sort videos by publication date
- Duplicates often appear near each other when sorted
- Check for videos with identical/similar titles published close together

## Action Plan

1. **For each video in your YouTube playlist (111 total):**
   - Check if its GUID matches one from the list above
   - If YES and it's the only video with that GUID → KEEP
   - If YES but there's another video with same GUID → Remove duplicates (keep newest)
   - If NO (GUID not in list) → REMOVE

2. **Expected Result:**
   - Exactly 73 videos remaining
   - Each video has a unique GUID matching the RSS feed

## Notes

- The RSS feed is the source of truth for what should be in YouTube
- YouTube automatically adds new episodes from RSS but doesn't remove old ones
- Manual cleanup is required to remove outdated/duplicate videos


