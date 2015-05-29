"
" VIM configuration
" @author christianru
"

" Use same indention as the previous line
set autoindent

" Re-read file if it was edited outside of vim (but not inside of vim or deleted)
set autoread

" Write the file if it has been modified
set autowrite

" Set character encoding for the file
set fileencoding=utf-8

" Underline cursor at current line
set cursorline

" Use spaces as indention
set expandtab

" Spaces to use for indention
set softtabstop=2

" Enable syntax highlighting
syntax enable

" Highlight previous search
set hlsearch

" Highlight what matches the search string as it is typed so far
set incsearch

" Enable the use of the mouse (a=enable mouse in all modes)
set mouse=a

" Enable the use of the mouse to focus on different windows
set mousefocus

" Hide mouse when typing characters
set mousehide

" Enable line numbers
set number

" Change color of the statusline
" au InsertEnter * hi StatusLine term=reverse ctermfg=0 ctermbg=2 gui=bold,reverse
" au InsertLeave * hi StatusLine term=reverse ctermfg=0 ctermbg=2 gui=bold,reverse

hi StatusLine ctermbg=3 ctermfg=0

" Modify the statusline to show usefull information
set statusline=Path:\ %f\ -\ Type:\ %y\ -\ Line:\ %l\ -\ Column:\ %c\ -\ Depth:\ %p%%\ -\ Modified:\ %m\ -\ Remarks:\ %r\ -\ %{hostname()}

set laststatus=2

" Keybindings

" Not able to map ctrl+s to save at this time
nnoremap <C-l> :w<CR>
nnoremap <C-v> :vsplit<CR>
nnoremap <C-h> :split<CR>

