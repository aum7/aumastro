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
badd +127 ui/mainpanes/chart/angleruler.py
badd +26 ~/dev/venaumastro/aumastro/ui/fonts/glyphs.py
badd +99 ~/dev/venaumastro/aumastro/user/settings.py
argglobal
%argdel
edit ui/mainpanes/chart/angleruler.py
argglobal
balt ~/dev/venaumastro/aumastro/ui/fonts/glyphs.py
let s:cpo_save=&cpo
set cpo&vim
inoremap <buffer> <M-e> l<Cmd>lua require('nvim-autopairs.fastwrap').show()
nnoremap <buffer> <silent> K <Cmd>lua vim.lsp.buf.hover()
nnoremap <buffer> <silent> gr <Cmd>lua vim.lsp.buf.references()
nnoremap <buffer> <silent> gD <Cmd>lua vim.lsp.buf.declaration()
nnoremap <buffer> <silent> gI <Cmd>lua vim.lsp.buf.implementation()
nnoremap <buffer> <silent> gd <Cmd>lua vim.lsp.buf.definition()
nnoremap <buffer> <silent> gs <Cmd>lua vim.lsp.buf.signature_help()
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
setlocal statusline=%#lualine_a_11_command#\ ����\ %#lualine_b_2_command#%#SLGitIcon#\ %*%#SLBranchName#\ angleruler\ %<%#lualine_c_diff_added_command#\ \ \ 18\ %#lualine_c_diff_modified_command#\ 5\ %#lualine_c_normal#%=%#lualine_x_diagnostics_hint_command#\ \ 6\ %#lualine_c_normal#%#lualine_c_normal#\ 󰌒\ 4\ %#lualine_x_filetype_DevIconPy_command#\ \ %#lualine_c_normal#python\ %#lualine_b_command#\ 127:37\ %#lualine_z_progress_command#\ %P/%L\ 
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
setlocal winbar=\ %#DevIconPy#%*\ %#Winbar#angleruler.py%*\ %#NavicSeparator#%*\ %#NavicIconsClass#\ %*%#NavicText#AngleRuler%*%#NavicSeparator#\ \ %*%#NavicIconsMethod#\ %*%#NavicText#on_scroll%*
setlocal winblend=0
setlocal winhighlight=
setlocal nowinfixheight
setlocal nowinfixwidth
setlocal wrap
setlocal wrapmargin=0
15
normal! zo
18
normal! zo
79
normal! zo
109
normal! zo
110
normal! zo
121
normal! zo
129
normal! zo
147
normal! zo
156
normal! zo
164
normal! zo
165
normal! zo
171
normal! zo
284
normal! zo
285
normal! zo
288
normal! zo
303
normal! zo
305
normal! zo
308
normal! zo
310
normal! zo
322
normal! zo
323
normal! zo
327
normal! zo
358
normal! zo
359
normal! zo
363
normal! zo
367
normal! zo
372
normal! zo
378
normal! zo
396
normal! zo
397
normal! zo
407
normal! zo
410
normal! zo
414
normal! zo
418
normal! zo
420
normal! zo
432
normal! zo
738
normal! zo
let s:l = 127 - ((16 * winheight(0) + 17) / 34)
if s:l < 1 | let s:l = 1 | endif
keepjumps exe s:l
normal! zt
keepjumps 127
normal! 037|
tabnext 1
if exists('s:wipebuf') && len(win_findbuf(s:wipebuf)) == 0 && getbufvar(s:wipebuf, '&buftype') isnot# 'terminal'
  silent exe 'bwipe ' . s:wipebuf
endif
unlet! s:wipebuf
set winheight=1 winwidth=20
let &shortmess = s:shortmess_save
let s:sx = expand("<sfile>:p:r")."x.vim"
if filereadable(s:sx)
  exe "source " . fnameescape(s:sx)
endif
let &g:so = s:so_save | let &g:siso = s:siso_save
set hlsearch
doautoall SessionLoadPost
unlet SessionLoad
" vim: set ft=vim :
