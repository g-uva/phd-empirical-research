/**
 * Color palette for graph viewer op nodes.
 * in format of [background color, border color, text color]
 * ref: hlo_graph_dumper.cc
 */
export const GRAPH_OP_COLORS: {[key: string]: string[]} = {
  'kBlue': ['#bbdefb', '#8aacc8', 'black'],
  'kBrown': ['#bcaaa4', '#8c7b75', 'black'],
  'kDarkBlue': ['#1565c0', '#003c8f', 'white'],
  'kDarkGreen': ['#2e7d32', '#005005', 'white'],
  'kGray': ['#cfd8dc', '#9ea7aa', 'black'],
  'kGreen': ['#c8e6c9', '#97b498', 'black'],
  'kOrange': ['#ffe0b2', '#cbae82', 'black'],
  'kPurple': ['#e1bee7', '#af8eb5', 'black'],
  'kYellow': ['#fff9c4', '#cbc693', 'black'],
};

/**
 * Color for graph viewer center node.
 */
export const GRAPH_CENTER_NODE_COLOR = [
  'rgb(255, 205, 210)',
  'rgb(183, 28, 28)',
  'black',
];
