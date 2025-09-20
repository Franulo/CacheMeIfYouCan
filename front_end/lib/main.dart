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

  String selectedTab = 'Realtime';
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
    final response = await http.post(
      Uri.parse('$baseUrl/search-news'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'topic': topic,
        'sources': selectedSources,
        'timeframe': selectedTab,
      }),
    );
    if (response.statusCode == 200) {
      setState(() {
        articles = json.decode(response.body);
        selectedArticleDetails = null;
      });
    }
  }

  Future<void> fetchArticleDetail(int id) async {
    final response = await http.get(Uri.parse('$baseUrl/article/$id'));
    if (response.statusCode == 200) {
      setState(() => selectedArticleDetails = json.decode(response.body));
    }
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
          width: 250, // adjust width as needed
          child: TextField(
            onChanged: (v) => topic = v,
            onSubmitted: (_) => fetchArticles(), // refresh on Enter
            decoration: InputDecoration(
              hintText: 'Search topic…',
              filled: true,
              fillColor: Colors.grey[200],
              border: OutlineInputBorder(
                borderSide: BorderSide.none,
                borderRadius: BorderRadius.circular(20),
              ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16),
            ),
          ),
        ),
        const SizedBox(width: 16),
        CompositedTransformTarget(
          link: _layerLink,
          child: ElevatedButton(
            key: _buttonKey,
            onPressed: _toggleSourcesMenu,
            style: ElevatedButton.styleFrom(backgroundColor: Colors.black),
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
            color: Colors.grey[200], // slightly grayer background
            child: Column(
              children: [
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children:
                      ['Realtime', 'Daily', 'Weekly', 'Monthly'].map((tab) {
                        final isSelected = selectedTab == tab;
                        return TextButton(
                          onPressed: () {
                            setState(() => selectedTab = tab);
                            fetchArticles(); // refresh on tab change
                          },
                          child: Text(
                            tab,
                            style: TextStyle(
                              color: isSelected ? Colors.black : Colors.grey,
                            ),
                          ),
                        );
                      }).toList(),
                ),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: articles.length,
                    itemBuilder: (context, index) {
                      final article = articles[index];
                      return GestureDetector(
                        onTap: () => fetchArticleDetail(article['id']),
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.grey[100],
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(
                                      article['title'],
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    article['time'] ?? '',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Text(article['summary']),
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
            padding: const EdgeInsets.all(16),
            child:
                selectedArticleDetails == null
                    ? const Center(child: Text('Select an article'))
                    : SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            selectedArticleDetails!['overview'],
                            style: const TextStyle(fontSize: 16),
                          ),
                          const SizedBox(height: 16),
                          Wrap(
                            spacing: 8,
                            children:
                                (selectedArticleDetails!['tags'] as List)
                                    .map((tag) => Chip(label: Text(tag)))
                                    .toList(),
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            'Live Ticker',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                          ...((selectedArticleDetails!['live_ticker'] as List)
                              .map(
                                (t) => Padding(
                                  padding: const EdgeInsets.all(4),
                                  child: Text(t),
                                ),
                              )),
                        ],
                      ),
                    ),
          ),
        ),
      ],
    ),
  );
}
