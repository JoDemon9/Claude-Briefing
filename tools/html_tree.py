"""A tiny, read-only HTML tree for indexing already published editions."""
from html.parser import HTMLParser
import re

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Node:
    def __init__(self, tag='', attrs=(), parent=None, offset=0):
        self.tag, self.attrs, self.parent, self.offset = tag, dict(attrs), parent, offset
        self.children = []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def has_class(self, name):
        return name in (self.attrs.get('class') or '').split()

    def text(self):
        def read(node):
            if isinstance(node, str):
                return node
            if node.tag in ('script', 'style'):
                return ''
            return ' '.join(read(child) for child in node.children)
        return re.sub(r'\s+', ' ', read(self)).strip()

    def closest(self, tag):
        node = self.parent
        while node:
            if node.tag == tag:
                return node
            node = node.parent


class Tree(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.root = Node()
        self.stack = [self.root]
        self.offsets = [0]
        for match in re.finditer('\n', source):
            self.offsets.append(match.end())
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        line, column = self.getpos()
        node = Node(tag, attrs, self.stack[-1], self.offsets[line - 1] + column)
        node.end_offset = node.offset + len(self.get_starttag_text())
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                line, column = self.getpos()
                self.stack[index].end_offset = self.source.find('>', self.offsets[line - 1] + column) + 1
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)
