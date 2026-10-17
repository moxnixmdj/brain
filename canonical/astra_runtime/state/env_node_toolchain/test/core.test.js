const test = require('node:test');
const assert = require('node:assert');
const { add, mul } = require('../core.js');
test('add works', () => assert.strictEqual(add(2, 3), 5));
test('mul works', () => assert.strictEqual(mul(4, 5), 20));
test('tags work', () => assert.strictEqual(require('../core.js').tags(['a','b']), 'a,b'));
