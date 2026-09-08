'use strict';
(() => {
  // The form URL and prefill field are verified from the live Google Form before release.
  const FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLSeL3Uv0vbKF_otHrs32-5oaCYg6SD_j_A6UUltKDDk9Pj69kQ/viewform';
  const CONSULT_ENTRY = 'entry.136188421';
  const questions = [
    {title:'いまのお仕事に近いのは？',options:['介護・医療・福祉','会社・お店の運営','個人で活動している','まずは、のぞきに来た'],reply:'なるほど。次は、相棒に頼みたいこと！'},
    {title:'ひとつ任せるなら、どれ？',options:['メモや記録をまとめる','研修・説明の資料をつくる','お知らせやHPをつくる','アイデアの壁打ちをする'],reply:'それ、相棒の出番がありそう。あとひとつ！'},
    {title:'AIとは、どのくらい仲良し？',options:['まだ使ったことがない','少し使ってみた','日々の仕事に使っている'],reply:'教えてくれてありがとう。こんな使い方はどう？'}
  ];
  const examples = [
    {title:'メモの整理は、\n相棒に。',intro:'思いつくままに書いたメモも、相手が読みやすい順番に整理する下書きに。',before:'来週火曜に研修。資料は金曜まで。新人さんも参加。場所は会議室。担当は自分。',after:'【研修のご案内・下書き】\n日時：来週火曜日（時間は要確認）\n場所：会議室\n対象：新人を含む職員\n準備：金曜までに資料を用意\n担当：案内者（氏名を確認）',next:'最初は、日付や固有名詞を伏せた会議メモひとつから。書いていないことを補わない指示も、一緒に整えます。'},
    {title:'伝え方を考える、\nもう一人。',intro:'研修のテーマを渡して、構成や練習問題のたたき台を相談できます。',before:'新人向けに、メモの残し方を説明したい。10分くらい。話を聞くだけでなく、自分で試してほしい。',after:'【10分研修の構成案】\n2分：誰に・何を伝えるメモか考える\n3分：日時・事実・次の行動に分ける\n3分：架空の会議メモを整理する\n2分：二人で読み比べ、抜けを確認',next:'まずは、いつもの説明をひとつ。現場のルールに合っているか確かめながら、職員さんが試せる資料を作りましょう。'},
    {title:'「伝えたい」を、\n一緒に形に。',intro:'思いはあるのに文章にできない。そんなときは、読み手と目的から一緒に整理します。',before:'職場見学に来てほしい。施設の雰囲気がわかる会にしたい。写真も載せたい。詳細はまだ決まっていない。',after:'【お知らせの構成案】\n見出し：まずは、職場の空気を見に来ませんか。\n紹介：普段の様子がわかる写真とひと言\n詳細：日時・場所・参加対象を確認して記載\n案内：申込方法と問い合わせ先を決める',next:'このホームページも、AIと一緒に作りました。誰に何を伝えたいかを出発点に、文章から見た目までご相談いただけます。'},
    {title:'考え途中でも、\n話せる相棒。',intro:'正解を出してもらうだけでなく、考えを広げる質問を返してもらう使い方も。',before:'職員同士で話す時間を増やしたい。でも、みんな忙しい。長い会議を増やしたいわけではない。',after:'【相棒からの問いの例】\n・まず誰と誰が話せると、うれしい？\n・今ある時間に、3分だけ足せそう？\n・困りごとと「よかったこと」、どちらから？\n・一週間だけ試すなら、何をする？',next:'答えが決まっていなくても大丈夫。人やチームの強みも聴きながら、まず試してみる一歩を一緒に見つけます。'}
  ];
  const $ = id => document.getElementById(id);
  const quiz=$('quiz'),result=$('result'),choices=$('choices'),guide=$('guide-message');
  let step=0,answers=[],showingAfter=false,transitioning=false;
  function consultURL(withAnswers=false){
    if(!FORM_URL) return '#contact';
    const url=new URL(FORM_URL);
    if(withAnswers && CONSULT_ENTRY){
      url.searchParams.set('usp','pp_url');
      url.searchParams.set(CONSULT_ENTRY,`【HPのミニアンケート】\n仕事：${questions[0].options[answers[0]]}\n任せたいこと：${questions[1].options[answers[1]]}\nAIとの距離：${questions[2].options[answers[2]]}\n\n【相談したいこと】\nこの使い方を自分の仕事でも試してみたいです。`);
    }
    return url.toString();
  }
  if(FORM_URL) document.querySelectorAll('.form-link').forEach(a=>a.href=consultURL());
  function render(focus=false){
    transitioning=false;quiz.hidden=false;result.hidden=true;
    $('question-title').textContent=questions[step].title;
    $('step-label').textContent=`0${step+1} / 03`;
    $('progress-fill').style.width=`${(step+1)/3*100}%`;
    $('quiz-back').hidden=step===0;
    choices.replaceChildren();
    questions[step].options.forEach((label,i)=>{
      const button=document.createElement('button');button.type='button';button.className='choice';button.textContent=label;
      button.setAttribute('aria-label',label);
      button.setAttribute('aria-pressed',String(answers[step]===i));
      button.addEventListener('click',()=>{
        if(transitioning)return;transitioning=true;answers[step]=i;
        button.setAttribute('aria-pressed','true');guide.textContent=questions[step].reply;
        const guideImage=document.querySelector('.guide img');guideImage.classList.remove('waving');
        requestAnimationFrame(()=>guideImage.classList.add('waving'));
        // A short beat makes the tap's response visible without simulating AI processing.
        setTimeout(()=>{if(step<2){step++;render(true);}else{showResult();}},180);
      });choices.append(button);
    });
    if(focus)$('question-title').focus({preventScroll:true});
  }
  function showResult(){
    quiz.hidden=true;result.hidden=false;showingAfter=false;transitioning=false;
    const example=examples[answers[1]];
    $('result-title').textContent=example.title;
    const sector=answers[0]===0?'まずは個人情報を含まない業務から。':answers[0]===1?'日々の業務のひとつから。':answers[0]===2?'ひとりで抱えている作業のひとつから。':'気になる場面を、ちょっとのぞいてみましょう。';
    $('result-intro').textContent=sector+example.intro;
    $('sample-content').textContent=example.before;$('sample-tag').textContent='手元のメモ';document.querySelector('.sample').classList.remove('is-done');
    $('partner-label').textContent='相棒、ちょっと手伝って！';$('sample-note').textContent='カピバラをタップして、整理した例を見てみよう。';
    const level=answers[2]===0?'最初の操作から、一緒に試せます。':answers[2]===1?'使ってみたときの困りごとも、聞かせてください。':'普段の使い方を伺って、もう一歩先を一緒に試しましょう。';
    $('result-next').textContent=example.next+' '+level;$('result-contact').href=consultURL(true);
    $('result-title').focus({preventScroll:true});
    $('play-board').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  }
  $('partner-button').addEventListener('click',()=>{
    showingAfter=!showingAfter;const example=examples[answers[1]];
    $('sample-content').textContent=showingAfter?example.after:example.before;
    $('sample-tag').textContent=showingAfter?'AIに手伝ってもらうと（例）':'手元のメモ';
    document.querySelector('.sample').classList.toggle('is-done',showingAfter);
    $('partner-label').textContent=showingAfter?'元のメモと見比べる':'相棒、ちょっと手伝って！';
    $('sample-note').textContent=showingAfter?'仕組みをイメージするための作成済みサンプルです。その場でAIを実行しているわけではありません。実務では人が内容を確認します。':'カピバラをタップして、整理した例を見てみよう。';
  });
  $('quiz-back').addEventListener('click',()=>{if(transitioning)return;step=Math.max(0,step-1);render(true);});
  $('quiz-restart').addEventListener('click',()=>{step=0;answers=[];guide.textContent='別の出番も、見てみよう！';render(true);});
  render();
})();
