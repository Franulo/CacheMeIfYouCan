import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: const NewsDashboard(),
    );
  }
}

class NewsDashboard extends StatefulWidget {
  const NewsDashboard({super.key});
  @override
  State<NewsDashboard> createState() => _NewsDashboardState();
}

class _NewsDashboardState extends State<NewsDashboard> {
  // Backend base URL
  final String baseUrl = 'http://127.0.0.1:5000';

  // UI state
  String selectedTab = 'Realtime';
  String topic = '';
  List<String> availableSources = ['New York Times', 'Bloomberg', 'Reuters'];
  List<String> selectedSources = [];
  List<dynamic> articles = [];
  Map<String, dynamic>? selectedArticleDetails;

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
      setState(() {
        selectedArticleDetails = json.decode(response.body);
      });
    }
  }

  void _showSourcesDialog() async {
    final result = await showDialog<List<String>>(
      context: context,
      builder: (context) {
        // make a copy so we don’t mutate original until Done is pressed
        List<String> tempSelected = List.from(selectedSources);

        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Select Sources'),
              content: SizedBox(
                width: 300,
                child: ListView(
                  shrinkWrap: true,
                  children:
                      availableSources.map((source) {
                        final isSelected = tempSelected.contains(source);
                        return CheckboxListTile(
                          title: Text(source),
                          value: isSelected,
                          onChanged: (bool? checked) {
                            setStateDialog(() {
                              if (checked == true) {
                                tempSelected.add(source);
                              } else {
                                tempSelected.remove(source);
                              }
                            });
                          },
                        );
                      }).toList(),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context, tempSelected),
                  child: const Text('Done'),
                ),
              ],
            );
          },
        );
      },
    );

    if (result != null) {
      setState(() {
        selectedSources = result;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 1,
        titleSpacing: 16,
        title: Row(
          children: [
            const Text(
              'Wellerhoffs Financial News Detection',
              style: TextStyle(
                color: Colors.black,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(width: 16),
            // Search topic input
            Expanded(
              child: TextField(
                onChanged: (v) => topic = v,
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
            // Multi-select sources
            ElevatedButton(
              onPressed: _showSourcesDialog,
              style: ElevatedButton.styleFrom(backgroundColor: Colors.black),
              child: Text(
                selectedSources.isEmpty
                    ? 'Select sources'
                    : selectedSources.join(', '),
                style: const TextStyle(color: Colors.white),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: fetchArticles,
              child: const Text('Search'),
            ),
          ],
        ),
      ),
      body: Row(
        children: [
          // LEFT SIDEBAR
          Expanded(
            flex: 2,
            child: Column(
              children: [
                // Tabs
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children:
                      ['Realtime', 'Daily', 'Weekly', 'Monthly']
                          .map(
                            (tab) => TextButton(
                              onPressed: () {
                                setState(() {
                                  selectedTab = tab;
                                });
                              },
                              child: Text(
                                tab,
                                style: TextStyle(
                                  color:
                                      selectedTab == tab
                                          ? Colors.black
                                          : Colors.grey,
                                ),
                              ),
                            ),
                          )
                          .toList(),
                ),
                const Divider(height: 1),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: articles.length,
                    itemBuilder: (context, index) {
                      final article = articles[index];
                      return GestureDetector(
                        onTap: () {
                          fetchArticleDetail(article['id']);
                        },
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
}
