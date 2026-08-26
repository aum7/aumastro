let SessionLoad = 1
let s:so_save = &g:so | let s:siso_save = &g:siso | setg so=0 siso=0 | setl so=-1 siso=-1
let v:this_session=expand("<sfile>:p")
silent only
silent tabonly
cd ~/dev/venaumastro/aumastro
if expand('%') == '' && !&modified && line('$') <= 1 && getline(1) == ''
  let s:wipebuf = bufnr('%')
endif
let s:shortmess_save = &shortmess
if &shortmess =~ 'A'
  set shortmess=aoOA
else
  set shortmess=aoO
endif
badd +54 ~/dev/venaumastro/aumastro/ui/datamanager.py
badd +14 ~/dev/venaumastro/aumastro/user/settings.py
argglobal
%argdel
edit ~/dev/venaumastro/aumastro/ui/datamanager.py
let s:save_splitbelow = &splitbelow
let s:save_splitright = &splitright
set splitbelow splitright
wincmd _ | wincmd |
split
1wincmd k
wincmd w
let &splitbelow = s:save_splitbelow
let &splitright = s:save_splitright
wincmd t
let s:save_winminheight = &winminheight
let s:save_winminwidth = &winminwidth
set winminheight=0
set winheight=1
set winminwidth=0
set winwidth=1
exe '1resize ' . ((&lines * 17 + 19) / 38)
exe '2resize ' . ((&lines * 17 + 19) / 38)
argglobal
balt ~/dev/venaumastro/aumastro/user/settings.py
let s:cpo_save=&cpo
set cpo&vim
inoremap <buffer> <M-e> l<Cmd>lua require('nvim-autopairs.fastwrap').show()
nnoremap <buffer> <silent> K <Cmd>lua vim.lsp.buf.hover()
nnoremap <buffer> <silent> gD <Cmd>lua vim.lsp.buf.declaration()
nnoremap <buffer> <silent> gd <Cmd>lua vim.lsp.buf.definition()
nnoremap <buffer> <silent> gs <Cmd>lua vim.lsp.buf.signature_help()
nnoremap <buffer> <silent> gI <Cmd>lua vim.lsp.buf.implementation()
nnoremap <buffer> <silent> gr <Cmd>lua vim.lsp.buf.references()
let &cpo=s:cpo_save
unlet s:cpo_save
setlocal keymap=
setlocal noarabic
setlocal autoindent
setlocal backupcopy=
setlocal nobinary
setlocal nobreakindent
setlocal breakindentopt=
setlocal bufhidden=
setlocal buflisted
setlocal buftype=
setlocal nocindent
setlocal cinkeys=0{,0},0),0],:,!^F,o,O,e
setlocal cinoptions=
setlocal cinwords=if,else,while,do,for,switch
setlocal cinscopedecls=public,protected,private
setlocal colorcolumn=
setlocal comments=b:#,fb:-
setlocal commentstring=#\ %s
setlocal complete=.,w,b,u,t
setlocal concealcursor=
setlocal conceallevel=0
setlocal completefunc=
setlocal nocopyindent
setlocal nocursorbind
setlocal nocursorcolumn
setlocal cursorline
setlocal cursorlineopt=both
setlocal define=^\\s*\\(def\\|class\\)
setlocal dictionary=
setlocal nodiff
setlocal equalprg=
setlocal errorformat=
setlocal expandtab
if &filetype != 'python'
setlocal filetype=python
endif
setlocal fillchars=
setlocal fixendofline
setlocal foldcolumn=0
setlocal foldenable
setlocal foldexpr=
setlocal foldignore=#
setlocal foldlevel=1
setlocal foldmarker={{{,}}}
setlocal foldmethod=indent
setlocal foldminlines=1
setlocal foldnestmax=20
setlocal foldtext=foldtext()
setlocal formatexpr=v:lua.vim.lsp.formatexpr(#{timeout_ms:500})
setlocal formatoptions=tcqj
setlocal formatlistpat=^\\s*\\d\\+[\\]:.)}\\t\ ]\\s*
setlocal formatprg=
setlocal grepprg=
setlocal iminsert=0
setlocal imsearch=-1
setlocal include=^\\s*\\(from\\|import\\)
setlocal includeexpr=substitute(substitute(substitute(v:fname,b:grandparent_match,b:grandparent_sub,''),b:parent_match,b:parent_sub,''),b:child_match,b:child_sub,'g')
setlocal indentexpr=python#GetIndent(v:lnum)
setlocal indentkeys=0{,0},0),0],:,!^F,o,O,e,<:>,=elif,=except
setlocal noinfercase
setlocal iskeyword=@,48-57,_,192-255
setlocal keywordprg=python3\ -m\ pydoc
setlocal linebreak
setlocal nolisp
setlocal lispoptions=
setlocal lispwords=
setlocal nolist
setlocal listchars=
setlocal makeencoding=
setlocal makeprg=
setlocal matchpairs=(:),{:},[:]
setlocal modeline
setlocal modifiable
setlocal nrformats=bin,hex
setlocal number
setlocal numberwidth=4
setlocal omnifunc=v:lua.vim.lsp.omnifunc
setlocal path=
setlocal nopreserveindent
setlocal nopreviewwindow
setlocal quoteescape=\\
setlocal noreadonly
setlocal relativenumber
setlocal norightleft
setlocal rightleftcmd=search
setlocal scrollback=-1
setlocal noscrollbind
setlocal scrolloff=-1
setlocal shiftwidth=4
setlocal showbreak=
setlocal sidescrolloff=-1
setlocal signcolumn=yes
setlocal nosmartindent
setlocal softtabstop=4
setlocal nospell
setlocal spellcapcheck=[.?!]\\_[\\])'\"\	\ ]\\+
setlocal spellfile=
setlocal spelllang=en,cjk
setlocal spelloptions=noplainbuffer
setlocal statuscolumn=
setlocal statusline=%#lualine_a_8_command#\ ����\ %#lualine_b_9_command#%#SLGitIcon#\ %*%#SLBranchName#\ angleruler\ %<%#lualine_c_diff_added_command#\ \ \ 190\ %#lualine_c_diff_modified_command#\ 81\ %#lualine_c_diff_removed_command#\ 49\ %#lualine_c_normal#%=%#lualine_x_diagnostics_warn_command#\ \ 13\ %#lualine_x_diagnostics_hint_command#\ 13\ %#lualine_c_normal#%#lualine_c_normal#\ 󰌒\ 4\ %#lualine_x_filetype_DevIconPy_command#\ \ %#lualine_c_normal#python\ %#lualine_b_command#\ \ 54:27\ %#lualine_z_progress_command#\ %P/%L\ 
setlocal suffixesadd=.py
setlocal noswapfile
setlocal synmaxcol=3000
if &syntax != ''
setlocal syntax=
endif
setlocal tagfunc=v:lua.vim.lsp.tagfunc
setlocal tabstop=4
setlocal tagcase=
setlocal tags=
setlocal textwidth=0
setlocal thesaurus=
setlocal thesaurusfunc=
setlocal undofile
setlocal undolevels=-123456
setlocal varsofttabstop=
setlocal vartabstop=
setlocal virtualedit=
setlocal winbar=\ %#DevIconPy#%*\ %#Winbar#datamanager.py%*\ %#NavicSeparator#%*\ %#NavicIconsClass#\ %*%#NavicText#DataManager%*%#NavicSeparator#\ \ %*%#NavicIconsMethod#\ %*%#NavicText#recalculate%*
setlocal winblend=0
setlocal winhighlight=
setlocal nowinfixheight
setlocal nowinfixwidth
setlocal wrap
setlocal wrapmargin=0
14
normal! zo
47
normal! zo
55
normal! zo
60
normal! zo
64
normal! zo
76
normal! zo
121
normal! zo
132
normal! zo
134
normal! zo
139
normal! zo
142
normal! zo
149
normal! zo
171
normal! zo
172
normal! zo
174
normal! zo
171
normal! zc
180
normal! zo
181
normal! zo
191
normal! zo
198
normal! zo
203
normal! zo
205
normal! zo
208
normal! zo
210
normal! zo
212
normal! zo
221
normal! zo
225
normal! zo
227
normal! zo
235
normal! zo
236
normal! zo
43
normal! zo
44
normal! zo
54
normal! zo
58
normal! zo
79
normal! zo
83
normal! zo
87
normal! zo
91
normal! zo
93
normal! zo
97
normal! zo
99
normal! zo
102
normal! zo
104
normal! zo
106
normal! zo
109
normal! zo
116
normal! zo
120
normal! zo
125
normal! zo
132
normal! zo
134
normal! zo
135
normal! zo
136
normal! zo
143
normal! zo
159
normal! zo
167
normal! zo
174
normal! zo
181
normal! zo
184
normal! zo
187
normal! zo
189
normal! zo
193
normal! zo
197
normal! zo
199
normal! zo
201
normal! zo
206
normal! zo
210
normal! zo
212
normal! zo
215
normal! zo
224
normal! zo
221
normal! zo
222
normal! zo
226
normal! zo
228
normal! zo
let s:l = 175 - ((7 * winheight(0) + 8) / 16)
if s:l < 1 | let s:l = 1 | endif
keepjumps exe s:l
normal! zt
keepjumps 175
normal! 036|
wincmd w
argglobal
if bufexists(fnamemodify("~/dev/venaumastro/aumastro/ui/datamanager.py", ":p")) | buffer ~/dev/venaumastro/aumastro/ui/datamanager.py | else | edit ~/dev/venaumastro/aumastro/ui/datamanager.py | endif
if &buftype ==# 'terminal'
  silent file ~/dev/venaumastro/aumastro/ui/datamanager.py
endif
balt ~/dev/venaumastro/aumastro/user/settings.py
let s:cpo_save=&cpo
set cpo&vim
inoremap <buffer> <M-e> l<Cmd>lua require('nvim-autopairs.fastwrap').show()
nnoremap <buffer> <silent> K <Cmd>lua vim.lsp.buf.hover()
nnoremap <buffer> <silent> gD <Cmd>lua vim.lsp.buf.declaration()
nnoremap <buffer> <silent> gd <Cmd>lua vim.lsp.buf.definition()
nnoremap <buffer> <silent> gs <Cmd>lua vim.lsp.buf.signature_help()
nnoremap <buffer> <silent> gI <Cmd>lua vim.lsp.buf.implementation()
nnoremap <buffer> <silent> gr <Cmd>lua vim.lsp.buf.references()
let &cpo=s:cpo_save
unlet s:cpo_save
setlocal keymap=
setlocal noarabic
setlocal autoindent
setlocal backupcopy=
setlocal nobinary
setlocal nobreakindent
setlocal breakindentopt=
setlocal bufhidden=
setlocal buflisted
setlocal buftype=
setlocal nocindent
setlocal cinkeys=0{,0},0),0],:,!^F,o,O,e
setlocal cinoptions=
setlocal cinwords=if,else,while,do,for,switch
setlocal cinscopedecls=public,protected,private
setlocal colorcolumn=
setlocal comments=b:#,fb:-
setlocal commentstring=#\ %s
setlocal complete=.,w,b,u,t
setlocal concealcursor=
setlocal conceallevel=0
setlocal completefunc=
setlocal nocopyindent
setlocal nocursorbind
setlocal nocursorcolumn
setlocal cursorline
setlocal cursorlineopt=both
setlocal define=^\\s*\\(def\\|class\\)
setlocal dictionary=
setlocal nodiff
setlocal equalprg=
setlocal errorformat=
setlocal expandtab
if &filetype != 'python'
setlocal filetype=python
endif
setlocal fillchars=
setlocal fixendofline
setlocal foldcolumn=0
setlocal foldenable
setlocal foldexpr=
setlocal foldignore=#
setlocal foldlevel=1
setlocal foldmarker={{{,}}}
setlocal foldmethod=indent
setlocal foldminlines=1
setlocal foldnestmax=20
setlocal foldtext=foldtext()
setlocal formatexpr=v:lua.vim.lsp.formatexpr(#{timeout_ms:500})
setlocal formatoptions=tcqj
setlocal formatlistpat=^\\s*\\d\\+[\\]:.)}\\t\ ]\\s*
setlocal formatprg=
setlocal grepprg=
setlocal iminsert=0
setlocal imsearch=-1
setlocal include=^\\s*\\(from\\|import\\)
setlocal includeexpr=substitute(substitute(substitute(v:fname,b:grandparent_match,b:grandparent_sub,''),b:parent_match,b:parent_sub,''),b:child_match,b:child_sub,'g')
setlocal indentexpr=python#GetIndent(v:lnum)
setlocal indentkeys=0{,0},0),0],:,!^F,o,O,e,<:>,=elif,=except
setlocal noinfercase
setlocal iskeyword=@,48-57,_,192-255
setlocal keywordprg=python3\ -m\ pydoc
setlocal linebreak
setlocal nolisp
setlocal lispoptions=
setlocal lispwords=
setlocal nolist
setlocal listchars=
setlocal makeencoding=
setlocal makeprg=
setlocal matchpairs=(:),{:},[:]
setlocal modeline
setlocal modifiable
setlocal nrformats=bin,hex
setlocal number
setlocal numberwidth=4
setlocal omnifunc=v:lua.vim.lsp.omnifunc
setlocal path=
setlocal nopreserveindent
setlocal nopreviewwindow
setlocal quoteescape=\\
setlocal noreadonly
setlocal relativenumber
setlocal norightleft
setlocal rightleftcmd=search
setlocal scrollback=-1
setlocal noscrollbind
setlocal scrolloff=-1
setlocal shiftwidth=4
setlocal showbreak=
setlocal sidescrolloff=-1
setlocal signcolumn=yes
setlocal nosmartindent
setlocal softtabstop=4
setlocal nospell
setlocal spellcapcheck=[.?!]\\_[\\])'\"\	\ ]\\+
setlocal spellfile=
setlocal spelllang=en,cjk
setlocal spelloptions=noplainbuffer
setlocal statuscolumn=
setlocal statusline=%#lualine_a_8_command#\ ����\ %#lualine_b_9_command#%#SLGitIcon#\ %*%#SLBranchName#\ angleruler\ %<%#lualine_c_diff_added_command#\ \ \ 190\ %#lualine_c_diff_modified_command#\ 81\ %#lualine_c_diff_removed_command#\ 49\ %#lualine_c_normal#%=%#lualine_x_diagnostics_warn_command#\ \ 13\ %#lualine_x_diagnostics_hint_command#\ 13\ %#lualine_c_normal#%#lualine_c_normal#\ 󰌒\ 4\ %#lualine_x_filetype_DevIconPy_command#\ \ %#lualine_c_normal#python\ %#lualine_b_command#\ \ 54:27\ %#lualine_z_progress_command#\ %P/%L\ 
setlocal suffixesadd=.py
setlocal noswapfile
setlocal synmaxcol=3000
if &syntax != ''
setlocal syntax=
endif
setlocal tagfunc=v:lua.vim.lsp.tagfunc
setlocal tabstop=4
setlocal tagcase=
setlocal tags=
setlocal textwidth=0
setlocal thesaurus=
setlocal thesaurusfunc=
setlocal undofile
setlocal undolevels=-123456
setlocal varsofttabstop=
setlocal vartabstop=
setlocal virtualedit=
setlocal winbar=\ %#DevIconPy#%*\ %#Winbar#datamanager.py%*\ %#NavicSeparator#%*\ %#NavicIconsClass#\ %*%#NavicText#DataManager%*
setlocal winblend=0
setlocal winhighlight=
setlocal nowinfixheight
setlocal nowinfixwidth
setlocal wrap
setlocal wrapmargin=0
43
normal! zo
44
normal! zo
54
normal! zo
58
normal! zo
79
normal! zo
116
normal! zo
120
normal! zo
132
normal! zo
134
normal! zo
135
normal! zo
143
normal! zo
159
normal! zo
167
normal! zo
174
normal! zo
181
normal! zo
184
normal! zo
187
normal! zo
189
normal! zo
193
normal! zo
197
normal! zo
199
normal! zo
201
normal! zo
206
normal! zo
210
normal! zo
212
normal! zo
215
normal! zo
224
normal! zo
221
normal! zo
222
normal! zo
226
normal! zo
228
normal! zo
let s:l = 54 - ((7 * winheight(0) + 8) / 16)
if s:l < 1 | let s:l = 1 | endif
keepjumps exe s:l
normal! zt
keepjumps 54
normal! 027|
wincmd w
2wincmd w
exe '1resize ' . ((&lines * 17 + 19) / 38)
exe '2resize ' . ((&lines * 17 + 19) / 38)
tabnext 1
if exists('s:wipebuf') && len(win_findbuf(s:wipebuf)) == 0 && getbufvar(s:wipebuf, '&buftype') isnot# 'terminal'
  silent exe 'bwipe ' . s:wipebuf
endif
unlet! s:wipebuf
set winheight=1 winwidth=20
let &shortmess = s:shortmess_save
let &winminheight = s:save_winminheight
let &winminwidth = s:save_winminwidth
let s:sx = expand("<sfile>:p:r")."x.vim"
if filereadable(s:sx)
  exe "source " . fnameescape(s:sx)
endif
let &g:so = s:so_save | let &g:siso = s:siso_save
set hlsearch
doautoall SessionLoadPost
unlet SessionLoad
" vim: set ft=vim :
