/**
 * Control discriminante de la suite: con el puntuador de thyrox (`scoreTaskReply`),
 * la traducción aceptada entre marcadores tiene que aprobar; el original en chino
 * entre marcadores y la traducción sin marcadores, suspender.
 */
import { readFileSync } from 'node:fs'

import { loadTaskSuite, scoreTaskReply } from '/home/user/thyrox/src/packages/local-models/taskSuite.ts'

const suite = await loadTaskSuite(process.argv[2] ?? '')
const asReply = (text: string) => `<<<ES\n${text}ES>>>`
let discriminates = true
for (const suiteCase of suite.cases) {
  const user = suiteCase.messages[1] as { content: string }
  const zhPath = /^Item: (.*)$/m.exec(user.content)?.[1] ?? ''
  const zh = readFileSync(zhPath, 'utf8')
  const reference = readFileSync(zhPath.replace('.zh.tex', '.es.tex'), 'utf8')
  const accepted = scoreTaskReply(suiteCase.checks, asReply(reference))
  const source = scoreTaskReply(suiteCase.checks, asReply(zh))
  const unmarked = scoreTaskReply(suiteCase.checks, reference)
  discriminates &&= accepted.passed && !source.passed && !unmarked.passed
  console.log(`${suiteCase.id}\tchecks=${suiteCase.checks.length}\taceptada=${accepted.passed}\tchino=${source.passed}\tsin-marcadores=${unmarked.passed}\t${accepted.failed.join('; ')}`)
}
console.log(discriminates ? 'discrimina' : 'NO discrimina')
process.exit(discriminates ? 0 : 1)
