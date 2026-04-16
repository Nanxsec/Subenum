<img width="1672" height="941" alt="subenum" src="https://github.com/user-attachments/assets/d50a0869-8cd6-4bdd-9b17-f808cff68020" />


# subenum

Enumerador de subdomínios, diretórios e virtual hosts escrito em Python puro. Sem dependências externas. Compatível com Python 3.8+.

---

## Visão Geral

subenum opera em três modos independentes, cada um voltado para uma superfície diferente durante o reconhecimento:

| Modo | Descrição |
|---|---|
| `sub` | Enumeração de subdomínios via resolução DNS com sondagem HTTP opcional |
| `dir` | Enumeração de diretórios e arquivos em uma URL alvo |
| `vhost` | Enumeração de virtual hosts via manipulação do cabeçalho `Host` |

Todos os modos utilizam I/O assíncrono com concorrência configurável, barra de progresso em tempo real e exportação opcional para arquivo.

---

## Instalação

```bash
git clone https://github.com/nanxsec/subenum
cd subenum
python3 subenum.py --help
python3 subenum.py dir --help -> mostra o help para fuzzing de diretório
python3 subenum.py sub --help -> mostra o help para fuzzing de subdominio
python3 subenum.py vhost --help -> mostra o help para fuzzing de virtual hosts
```

Nenhuma dependência adicional é necessária. Apenas Python 3.8 ou superior.

---

## Modos de Uso

### sub — Enumeração de Subdomínios

Resolve subdomínios contra um domínio alvo via DNS. Opcionalmente, sonda cada host resolvido por HTTP/HTTPS para coletar códigos de status, tamanhos de resposta, títulos de página e redirecionamentos.

**Detecção de wildcard DNS:** antes do início da varredura, três subdomínios aleatórios são resolvidos. Caso algum resolva, o IP e o hash do corpo da resposta são registrados e utilizados para suprimir falsos positivos durante toda a execução.

**Detecção de subdomain takeover:** as respostas são confrontadas com assinaturas conhecidas de serviços como GitHub Pages, Heroku, Amazon S3, Netlify, Shopify, Ghost, Zendesk, Surge.sh, Fastly, Azure, Tumblr e WordPress. Qualquer correspondência é sinalizada inline e consolidada em um bloco ao final da execução.

**Uso**

```bash
python3 subenum.py sub <domínio> -w <wordlist> [opções]
```

**Exemplo**

```bash
python3 subenum.py sub target.com -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -t 150 -o resultados.txt
```

**Opções**

| Flag | Padrão | Descrição |
|---|---|---|
| `domínio` | — | Domínio base alvo, ex: `target.com` |
| `-w`, `--wordlist` | — | Caminho para o arquivo de wordlist |
| `-t`, `--threads` | `100` | Número de workers concorrentes |
| `--timeout` | `5` | Timeout por requisição em segundos |
| `--dns-only` | `false` | Resolve apenas via DNS, ignora a sondagem HTTP |
| `--fc` | `404` | Filtra códigos de status HTTP, ex: `404,403` |
| `-o`, `--output` | — | Salva os resultados em arquivo |

**Colunas de saída**

```
SUBDOMAIN   IP   STATUS   SIZE   TITLE
```

Candidatos a takeover aparecem com a tag `[TAKEOVER: <serviço>]` na linha e são listados novamente em um bloco de resumo ao final.

---

### dir — Enumeração de Diretórios

Enumera caminhos e arquivos em um servidor web alvo. Antes do início da varredura, uma baseline de soft-404 é estabelecida requisitando um caminho gerado aleatoriamente. Essa baseline é utilizada ao longo da execução para suprimir respostas catch-all que, de outra forma, inundariam os resultados com falsos positivos.

A ferramenta também compara cada resposta com o hash da página inicial para descartar conteúdo genérico retornado independentemente do caminho requisitado.

**Fuzzing de extensões:** ao fornecer `-x php,html,txt`, uma requisição adicional é gerada por palavra por extensão, além do caminho sem extensão.

**Uso**

```bash
python3 subenum.py dir <url> -w <wordlist> [opções]
```

**Exemplo**

```bash
python3 subenum.py dir https://target.com -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -x php,html -t 80
```

**Opções**

| Flag | Padrão | Descrição |
|---|---|---|
| `url` | — | URL completa do alvo incluindo o esquema, ex: `https://target.com` |
| `-w`, `--wordlist` | — | Caminho para o arquivo de wordlist |
| `-t`, `--threads` | `50` | Número de workers concorrentes |
| `--timeout` | `5` | Timeout por requisição em segundos |
| `-x`, `--ext` | — | Extensões separadas por vírgula, ex: `php,html,txt` |
| `--fc` | `404` | Filtra códigos de status HTTP |
| `-o`, `--output` | — | Salva os resultados em arquivo |

**Colunas de saída**

```
PATH   STATUS   SIZE   TITLE / REDIRECT
```

Redirecionamentos são exibidos inline com o indicador `→ <destino>`.

---

### vhost — Enumeração de Virtual Hosts

Envia requisições a um IP alvo alternando o cabeçalho `Host` entre cada palavra da wordlist, formatada como `<palavra>.<domínio>`. Isso permite identificar virtual hosts que não estão expostos via DNS.

Uma baseline é coletada antes da varredura usando três nomes de vhost gerados aleatoriamente. A baseline captura códigos de status, tamanhos de resposta, contagem de palavras, contagem de linhas e hashes de corpo. Esses dados são utilizados durante a varredura para suprimir respostas catch-all automaticamente.

O comportamento de filtragem e correspondência segue as convenções do ffuf, facilitando a transição entre ferramentas.

**Uso**

```bash
python3 subenum.py vhost <domínio> -w <wordlist> [opções]
```

**Exemplo**

```bash
python3 subenum.py vhost target.thm -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt --ip 10.10.10.5 --port 80 --fw 300
```

**Opções**

| Flag | Padrão | Descrição |
|---|---|---|
| `domínio` | — | Domínio base para construção dos cabeçalhos vhost, ex: `target.thm` |
| `-w`, `--wordlist` | — | Caminho para o arquivo de wordlist |
| `--ip` | — | IP do alvo. Se omitido, o domínio é resolvido via DNS |
| `--port` | `80` | Porta do alvo |
| `--ssl` | `false` | Utiliza HTTPS |
| `-t`, `--threads` | `50` | Número de workers concorrentes |
| `--timeout` | `5` | Timeout por requisição em segundos |
| `--mc` | `200,301,302,307,401,403` | Corresponde apenas aos códigos de status indicados |
| `--fc` | — | Filtra códigos de status, ex: `400,404` |
| `--fs` | — | Filtra tamanhos de resposta exatos, ex: `1583` |
| `--fw` | — | Filtra respostas pelo número de palavras, ex: `236` |
| `--fl` | — | Filtra respostas pelo número de linhas, ex: `35` |
| `--ms` | — | Corresponde apenas a tamanhos de resposta exatos |
| `-o`, `--output` | — | Salva os resultados em arquivo |

**Colunas de saída**

```
VHOST   STATUS   SIZE   WORDS   LINES   TITLE
```

Quando o servidor retorna respostas catch-all, utilize `--fw` ou `--fs` para filtrar pelo valor da baseline exibido no cabeçalho de execução.

---

## Filtros e Supressão de Falsos Positivos

Cada modo implementa sua própria estratégia de detecção de falsos positivos:

**sub:** wildcard DNS detectado por resolução de subdomínios aleatórios antes da varredura. O hash MD5 do corpo da resposta wildcard é comparado com cada resultado para descartar conteúdo genérico.

**dir:** baseline estabelecida por requisição a um caminho inexistente aleatório. Respostas com hash idêntico ao da baseline, à página inicial, ou com tamanho dentro de 5% da baseline com o mesmo código de status são descartadas.

**vhost:** três amostras de vhosts aleatórios são coletadas. Respostas com hash idêntico, redirecionamento para o mesmo destino, ou com tamanho e contagem de palavras dentro de 5% da média da baseline são descartadas automaticamente. Filtros manuais (`--fw`, `--fs`, `--fl`, `--fc`) têm precedência sobre a filtragem automática.

---

## Saída em Arquivo

Todos os modos aceitam `-o <arquivo>` para exportar os resultados.

**sub:** cada linha contém o subdomínio, código de status e, quando aplicável, a tag `[TAKEOVER:<serviço>]`.

**dir:** cada linha contém o caminho, código de status, tamanho em bytes e redirecionamento quando presente.

**vhost:** cada linha contém o vhost, código de status, tamanho, contagem de palavras, contagem de linhas e redirecionamento quando presente.

---

## Requisitos

- Python 3.8+
- Sem dependências externas

---

## Aviso Legal

Esta ferramenta deve ser utilizada exclusivamente em ambientes para os quais você possui autorização explícita. O uso não autorizado contra sistemas de terceiros pode constituir violação de leis locais e internacionais de crimes cibernéticos.
