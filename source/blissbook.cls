\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{blissbook}[2026/08/29 Semantic LuaLaTeX edition of Bliss]

\LoadClass[
  UTF8,
  zihao=false,
  scheme=plain,
  fontset=none,
  twoside,
  openany
]{ctexbook}

\RequirePackage{fontspec}
\RequirePackage{geometry}
\RequirePackage{fancyhdr}
\RequirePackage{multicol}
\RequirePackage{hyperref}
\RequirePackage{bookmark}

% The live InDesign text area is 321 x 535 pt inside a 432 x 648 pt page.
\geometry{
  paperwidth=432bp,
  paperheight=648bp,
  inner=69bp,
  outer=42bp,
  top=47bp,
  bottom=66bp,
  headheight=0bp,
  headsep=0bp,
  footskip=29bp
}

\defaultfontfeatures{Ligatures=TeX}
\setmainfont{MinionPro-Regular.otf}[
  Path=fonts/,
  BoldFont=MinionPro-Bold.otf
]
\setCJKmainfont{FZNewShuSong-Z10.ttf}[
  Path=fonts/,
  BoldFont=FZNewShuSong-Z10.ttf,
  BoldFeatures={FakeBold=2}
]
\setCJKfamilyfont{blisstitlebyline}{FZNewShuSong-Z10S.ttf}[Path=fonts/]
\newfontfamily\BlissSymbols{AdobeSongStd-Light.otf}[Path=fonts/]
\newcommand{\BlissTitleBylineFont}{\CJKfamily{blisstitlebyline}}

% Hiragino is used by the InDesign edition but was not included by Package.
% Use it when the licensed system font is present; retain a TeX Live fallback.
\IfFontExistsTF{Hiragino Sans GB W6}{
  \setCJKfamilyfont{blissheading}{Hiragino Sans GB W6}
}{
  \setCJKfamilyfont{blissheading}{FandolHei-Bold.otf}
}
\newfontfamily\BlissHeadingLatin{texgyreheros-bold.otf}
\newcommand{\BlissHeadingFont}{%
  \CJKfamily{blissheading}\BlissHeadingLatin
}

\hypersetup{
  unicode=true,
  pdftitle={幸福},
  pdfauthor={李葆春},
  hidelinks,
  bookmarksnumbered=false
}

\newcommand{\BookBodyFont}{\fontsize{11bp}{18.7bp}\selectfont}
\AtBeginDocument{\BookBodyFont}
\setlength{\parindent}{22bp}
\setlength{\parskip}{5pt}
\setlength{\columnsep}{22pt}
\tolerance=2000
\emergencystretch=2em
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000

\fancypagestyle{blissbody}{%
  \fancyhf{}
  \fancyfoot[C]{\fontsize{8bp}{9bp}\selectfont\thepage}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}
}
\pagestyle{blissbody}

\newcommand{\BookLineBreak}{\linebreak}
\newcommand{\BookTab}{\hspace{1em}}

\newcommand{\BookParagraph}[1]{%
  \par\BookBodyFont\noindent\hspace{\parindent}#1\par
}
\newcommand{\BookPlainParagraph}[1]{\BookParagraph{#1}}
\newcommand{\BookDate}[1]{%
  \par\vspace{7bp}\noindent\hfill\BookBodyFont #1\par
}
\newcommand{\BookSubtitle}[1]{%
  \par\vspace{14bp}\noindent
  {\BlissHeadingFont\fontsize{11bp}{18.7bp}\selectfont #1}\par\vspace{7bp}
}
\newcommand{\BookFootnote}[1]{%
  \par\vspace{5bp}\noindent\fontsize{9bp}{14bp}\selectfont #1\par
  \BookBodyFont
}

\newcommand{\BookColophon}[1]{%
  \hypersetup{pageanchor=false}
  \pagenumbering{gobble}
  \thispagestyle{empty}\null\clearpage
  \thispagestyle{empty}
  \vspace*{72bp}
  \noindent\hspace*{12bp}%
  \begin{minipage}{285bp}
    \fontsize{7.2bp}{11.5bp}\selectfont\raggedright #1
  \end{minipage}
  \clearpage
}

\newcommand{\BookTitlePage}[4]{%
  \thispagestyle{empty}
  \vspace*{52bp}
  \begin{center}
    \begin{minipage}[t]{110bp}
      \hfill
      {\BlissHeadingFont\fontsize{26bp}{32bp}\selectfont\shortstack{#3}}
    \end{minipage}
    \hspace{24bp}
    \begin{minipage}[t]{85bp}
      \vspace{120bp}
      \centering\BlissTitleBylineFont\fontsize{12bp}{20bp}\selectfont
      \shortstack{#4\\著}
    \end{minipage}
  \end{center}
  \clearpage
  \thispagestyle{empty}\null\clearpage
}

\newcommand{\BookFrontHeading}[1]{%
  \clearpage
  \thispagestyle{empty}
  \vspace*{29bp}
  \begin{center}
    {\BlissHeadingFont\fontsize{16bp}{20bp}\selectfont #1}
  \end{center}
  \vspace{31bp}
  \BookBodyFont
}
\newcommand{\BookForeword}[1]{\BookFrontHeading{#1}}
\newcommand{\BookPreface}[1]{\BookFrontHeading{#1}}

\makeatletter
\renewcommand*\l@part[2]{%
  \addpenalty{-\@highpenalty}%
  \vspace{9bp}%
  {\BlissHeadingFont\fontsize{12bp}{18.7bp}\selectfont #1\par}%
}
\renewcommand*\l@section[2]{%
  \@dottedtocline{1}{0pt}{0pt}{#1}{#2}%
}
\newcommand{\BookTOC}{%
  \cleardoublepage
  \thispagestyle{empty}
  \vspace*{8bp}
  \begin{center}
    {\BlissHeadingFont\fontsize{16bp}{20bp}\selectfont 目\hspace{0.5em}录}
  \end{center}
  \vspace{17bp}
  \begingroup
    \pagestyle{empty}
    \setlength{\parskip}{0pt}
    \fontsize{11bp}{18.7bp}\selectfont
    \begin{multicols}{2}
      \@starttoc{toc}%
    \end{multicols}
  \endgroup
  \clearpage
  \thispagestyle{empty}\null\clearpage
}
\makeatother

\newcounter{bookpart}
\newcommand{\BookPart}[2]{%
  \cleardoublepage
  \stepcounter{bookpart}
  \phantomsection
  \addcontentsline{toc}{part}{#1}
  \thispagestyle{empty}
  \vspace*{35bp}
  \begin{center}
    {\BlissHeadingFont\fontsize{26bp}{34bp}\selectfont\shortstack{#2}}
  \end{center}
  \cleardoublepage
  \ifnum\value{bookpart}=1
    \hypersetup{pageanchor=true}%
    \pagenumbering{arabic}%
  \fi
}

\newcommand{\BookArticle}[2]{%
  \clearpage
  \phantomsection
  \addcontentsline{toc}{section}{#2}
  \thispagestyle{blissbody}
  \vspace*{133bp}
  \begin{center}
    {\BlissHeadingFont\fontsize{16bp}{21bp}\selectfont #1}
  \end{center}
  \vspace{29bp}
  \BookBodyFont
}

% The reference edition reserves body pages 382--384 as end matter blanks.
% Reflow can move the final article by a page, so pad to the same 384-page
% body instead of relying on a fixed number of blank-page commands.
\newcommand{\BookFinish}{%
  \clearpage
  \ifnum\value{page}<382
    \ClassError{blissbook}{Book body ended before page 381}{%
      The extracted book may be incomplete; refusing to conceal it with padding.}%
  \fi
  \pagestyle{empty}%
  \loop\ifnum\value{page}<385
    \thispagestyle{empty}\null\clearpage
  \repeat
}
