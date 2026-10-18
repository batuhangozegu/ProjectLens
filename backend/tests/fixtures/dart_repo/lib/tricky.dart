// TODO actual marker
/* nested /* FIXME actual */ TODO */
const raw = r'''TODO { class Hidden {} }''';
const text = '''TODO ${'class Nope { }'} { if (true) {} }''';
class Visible {
  String get label => 'ok';
  void work() { if (true) { print('no symbol'); } }
}
