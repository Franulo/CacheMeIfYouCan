import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    home: const NewsDashboard(),
  );
}

class NewsDashboard extends StatefulWidget {
  const NewsDashboard({super.key});
  @override
  State<NewsDashboard> createState() => _NewsDashboardState();
}

class _NewsDashboardState extends State<NewsDashboard> {
  final String baseUrl = 'http://127.0.0.1:5000';

  String selectedTab = 'Daily';
  String topic = '';
  List<String> availableSources = ['New York Times', 'Bloomberg', 'Reuters'];
  List<String> selectedSources = [];
  List<dynamic> articles = [];
  Map<String, dynamic>? selectedArticleDetails;

  final LayerLink _layerLink = LayerLink();
  OverlayEntry? _overlayEntry;
  bool sourcesMenuOpen = false;
  final GlobalKey _buttonKey = GlobalKey();

  void _toggleSourcesMenu() {
    if (sourcesMenuOpen) {
      _overlayEntry?.remove();
      sourcesMenuOpen = false;
    } else {
      final RenderBox renderBox =
          _buttonKey.currentContext!.findRenderObject() as RenderBox;
      final buttonSize = renderBox.size;
      final buttonOffset = renderBox.localToGlobal(Offset.zero);
      final screenWidth = MediaQuery.of(context).size.width;
      final overlayWidth = 250.0;

      // Ensure overlay doesn't go offscreen to the right
      double dx = buttonOffset.dx;
      if (dx + overlayWidth > screenWidth) {
        dx = screenWidth - overlayWidth - 8; // small padding
      }

      _overlayEntry = OverlayEntry(
        builder:
            (context) => GestureDetector(
              behavior: HitTestBehavior.translucent,
              onTap: () {
                _overlayEntry?.remove();
                sourcesMenuOpen = false;
                setState(() {});
              },
              child: Stack(
                children: [
                  Positioned(
                    left: dx,
                    top:
                        buttonOffset.dy + buttonSize.height + 4, // below button
                    width: overlayWidth,
                    child: Material(
                      elevation: 4,
                      borderRadius: BorderRadius.circular(8),
                      child: ConstrainedBox(
                        constraints: BoxConstraints(
                          maxHeight: MediaQuery.of(context).size.height * 0.6,
                        ),
                        child: StatefulBuilder(
                          builder:
                              (context, setOverlayState) => ListView(
                                shrinkWrap: true,
                                padding: const EdgeInsets.all(8),
                                children:
                                    availableSources.map((source) {
                                      return SwitchListTile(
                                        title: Text(source),
                                        value: selectedSources.contains(source),
                                        onChanged: (val) {
                                          setOverlayState(() {
                                            if (val) {
                                              selectedSources.add(source);
                                            } else {
                                              selectedSources.remove(source);
                                            }
                                          });
                                          fetchArticles();
                                        },
                                      );
                                    }).toList(),
                              ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
      );

      Overlay.of(context).insert(_overlayEntry!);
      sourcesMenuOpen = true;
    }
  }

  Future<void> fetchArticles() async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/search-news'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'year': 2024,
              'month': 1,
              'custom_search': topic,
              'tabType': selectedTab,
            }),
          )
          .timeout(const Duration(minutes: 5));

      if (response.statusCode != 200) {
        print('HTTP error: ${response.statusCode}');
        print('Response body: ${response.body}');
        return;
      }

      final Map<String, dynamic> jsonBody = json.decode(response.body);
      final dynamic data = jsonBody['data'];

      List<dynamic> tArticles = [];

      if (data is Map<String, dynamic>) {
        // Handle backend error
        if (data.containsKey('error')) {
          print('Backend error: ${data['error']}');
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Error: ${data['error']}'),
              backgroundColor: Colors.red,
            ),
          );
        } else {
          List<dynamic> overviewList = [];

          // Choose correct key based on selectedTab
          switch (selectedTab) {
            case "Daily":
              overviewList = data['daily_overviews'] ?? [];
              break;
            case "Weekly":
              overviewList = data['weekly_overviews'] ?? [];
              break;
            case "Monthly":
              final monthly = data['monthly_overview'];
              if (monthly != null && monthly['topics'] != null) {
                tArticles = monthly['topics'];
              }
              break;
            default:
              overviewList = data['daily_overviews'] ?? [];
          }

          // For Daily and Weekly, extract topics
          if (selectedTab != "Monthly") {
            tArticles =
                overviewList.expand((item) {
                  if (item is Map<String, dynamic>) {
                    final topics = (item['topics'] as List<dynamic>?) ?? [];
                    return topics.where(
                      (topic) =>
                          topic is Map<String, dynamic> &&
                          topic['title'] != null,
                    );
                  }
                  return [];
                }).toList();
          }
        }
      }

      print('Loaded ${tArticles.length} articles');

      setState(() {
        articles = tArticles;
        selectedArticleDetails = null;
      });
    } catch (e) {
      print('Error fetching articles: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Network error: $e'),
          backgroundColor: Colors.red,
        ),
      );
      setState(() {
        articles = [];
        selectedArticleDetails = null;
      });
    }
  }

  @override
  void initState() {
    super.initState();
    // Fetch articles when the app starts
    fetchArticles();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      backgroundColor: Colors.white,
      elevation: 1,
      titleSpacing: 16,
      title: const Text(
        'Wellerhoffs Financial News Detection',
        style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold),
      ),
      actions: [
        SizedBox(
          width: 250,
          child: TextField(
            onChanged: (v) => topic = v,
            onSubmitted: (_) => fetchArticles(),
            decoration: InputDecoration(
              hintText: 'Search topic…',
              filled: true,
              fillColor: Colors.grey[200],
              border: OutlineInputBorder(
                borderSide: BorderSide.none,
                borderRadius: BorderRadius.circular(20),
              ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16),
              suffixIcon: IconButton(
                icon: const Icon(Icons.search),
                onPressed: fetchArticles,
              ),
            ),
          ),
        ),
        const SizedBox(width: 16),
        CompositedTransformTarget(
          link: _layerLink,
          child: ElevatedButton(
            key: _buttonKey,
            onPressed: _toggleSourcesMenu,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.black,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
            child: const Text(
              'Select sources',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ),
        const SizedBox(width: 10),
      ],
    ),

    body: Row(
      children: [
        // LEFT SIDEBAR
        Expanded(
          flex: 2,
          child: Container(
            color: Colors.grey[200],
            child: Column(
              children: [
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children:
                      ['Daily', 'Weekly', 'Monthly'].map((tab) {
                        final isSelected = selectedTab == tab;
                        return TextButton(
                          onPressed: () {
                            setState(() => selectedTab = tab);
                            fetchArticles();
                          },
                          style: TextButton.styleFrom(
                            backgroundColor:
                                isSelected
                                    ? Colors.grey[300]
                                    : Colors.transparent,
                          ),
                          child: Text(
                            tab,
                            style: TextStyle(
                              color:
                                  isSelected ? Colors.black : Colors.grey[600],
                              fontWeight:
                                  isSelected
                                      ? FontWeight.bold
                                      : FontWeight.normal,
                            ),
                          ),
                        );
                      }).toList(),
                ),
                Expanded(
                  child:
                      articles.isEmpty
                          ? const Center(
                            child: Text(
                              'No articles found',
                              style: TextStyle(color: Colors.grey),
                            ),
                          )
                          : ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: articles.length,
                            itemBuilder: (context, index) {
                              final article = articles[index];
                              return GestureDetector(
                                onTap: () {
                                  setState(() {
                                    selectedArticleDetails = article;
                                  });
                                },
                                child: Container(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color:
                                        selectedArticleDetails == article
                                            ? Colors.blue[50]
                                            : Colors.grey[100],
                                    borderRadius: BorderRadius.circular(12),
                                    border:
                                        selectedArticleDetails == article
                                            ? Border.all(
                                              color: Colors.blue,
                                              width: 2,
                                            )
                                            : null,
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        article['title'] ?? 'No title',
                                        style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 16,
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        article['summary'] ??
                                            'No summary available',
                                        style: TextStyle(
                                          color: Colors.grey[700],
                                          fontSize: 14,
                                        ),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 8),
                                      if (article['relevance'] != null)
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 8,
                                            vertical: 4,
                                          ),
                                          decoration: BoxDecoration(
                                            color:
                                                article['relevance'] == 'high'
                                                    ? Colors.green[100]
                                                    : article['relevance'] ==
                                                        'medium'
                                                    ? Colors.orange[100]
                                                    : Colors.grey[100],
                                            borderRadius: BorderRadius.circular(
                                              12,
                                            ),
                                          ),
                                          child: Text(
                                            'Relevance: ${article['relevance']}',
                                            style: TextStyle(
                                              color:
                                                  article['relevance'] == 'high'
                                                      ? Colors.green[800]
                                                      : article['relevance'] ==
                                                          'medium'
                                                      ? Colors.orange[800]
                                                      : Colors.grey[800],
                                              fontSize: 12,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                ),
              ],
            ),
          ),
        ),

        // RIGHT PANEL
        Expanded(
          flex: 3,
          child: Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
            ),
            child:
                selectedArticleDetails == null
                    ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.article, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text(
                            'Select an article to view details',
                            style: TextStyle(color: Colors.grey, fontSize: 18),
                          ),
                        ],
                      ),
                    )
                    : SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            selectedArticleDetails!['title'] ?? 'No title',
                            style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 16),

                          Text(
                            selectedArticleDetails!['summary'] ??
                                'No summary available',
                            style: const TextStyle(fontSize: 16, height: 1.5),
                          ),

                          const SizedBox(height: 24),

                          if (selectedArticleDetails!['tags'] != null &&
                              selectedArticleDetails!['tags'] is List &&
                              (selectedArticleDetails!['tags'] as List)
                                  .isNotEmpty)
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Tags:',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children:
                                      (selectedArticleDetails!['tags'] as List)
                                          .map(
                                            (tag) => Chip(
                                              label: Text(tag.toString()),
                                              backgroundColor: Colors.blue[50],
                                            ),
                                          )
                                          .toList(),
                                ),
                                const SizedBox(height: 24),
                              ],
                            ),

                          if (selectedArticleDetails!['url'] != null &&
                              selectedArticleDetails!['url']
                                  .toString()
                                  .isNotEmpty)
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Original Article:',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                GestureDetector(
                                  onTap: () {
                                    // Could launch URL here
                                  },
                                  child: Text(
                                    selectedArticleDetails!['url'],
                                    style: TextStyle(
                                      color: Colors.blue[800],
                                      decoration: TextDecoration.underline,
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 24),
                              ],
                            ),

                          const Text(
                            'Generate Content:',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          const SizedBox(height: 16),

                          Row(
                            children: [
                              ElevatedButton(
                                onPressed: () {},
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.black,
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 20,
                                    vertical: 12,
                                  ),
                                ),
                                child: const Text(
                                  'LinkedIn Post',
                                  style: TextStyle(color: Colors.white),
                                ),
                              ),
                              const SizedBox(width: 12),
                              ElevatedButton(
                                onPressed: () {},
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.black,
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 20,
                                    vertical: 12,
                                  ),
                                ),
                                child: const Text(
                                  'Podcast Script',
                                  style: TextStyle(color: Colors.white),
                                ),
                              ),
                              const SizedBox(width: 12),
                              ElevatedButton(
                                onPressed: () {},
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.black,
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 20,
                                    vertical: 12,
                                  ),
                                ),
                                child: const Text(
                                  'Client Newsletter',
                                  style: TextStyle(color: Colors.white),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
          ),
        ),
      ],
    ),
  );
}
