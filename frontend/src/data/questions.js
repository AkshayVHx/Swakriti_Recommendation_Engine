export const QUESTIONS = [
  { id: 'gender', text: 'Who are we finding this outfit for?', type: 'single',
    options: ['Myself (woman)', 'Myself (man)', 'My child'] },
  { id: 'child_gender', text: 'What gender are we shopping for?', type: 'single',
    options: ['Girl', 'Boy'] },
  { id: 'size', text: 'What size should we find?', type: 'single',
    options: ['XS','S','M','L','XL','XXL','3XL','Not sure'] },
  { id: 'size_kids', text: 'What size should we find?', type: 'single',
    options: ['Age 0-2','Age 3-5','Age 6-8','Age 9-12','Age 13-14'] },
  { id: 'budget', text: "What's your budget for today?", type: 'single',
    options: ['Under 1000','1000-2500','2500-5000','5000-10000','10000+'] },
  { id: 'intent', text: 'What are you looking for today?', type: 'multi',
    options: ['Complete outfit','Top / kurti only','Dupatta / stole','Kidswear','Accessories','Something customised','Just exploring'] },
  { id: 'occasion', text: "What's the occasion?", type: 'single',
    options: ['Wedding / Reception','Festival / Puja','Party / Celebration','Office / College','Casual / Daily wear','Photoshoot','Travel / Vacation','Religious function','Birthday','Other / Tell me'] },
  { id: 'occasion_detail_wedding', text: 'Which wedding function?', type: 'single',
    options: ['Haldi','Mehendi','Sangeet','Reception','Ceremony','Engagement'] },
  { id: 'occasion_detail_festival', text: 'Which festival?', type: 'single',
    options: ['Onam','Diwali','Eid','Pongal','Vishu','Navratri','Other'] },
  { id: 'occasion_detail_office', text: 'Which one?', type: 'single',
    options: ['Office','College'] },
  { id: 'style', text: 'What style feels like you?', type: 'single',
    options: ['Traditional / Classic ethnic','Indo-western','Modern / Minimal ethnic','Trendy / Bold','Comfortable first','Premium / Luxury','Cute / Feminine'] },
  { id: 'colour', text: 'Any colour preference?', type: 'multi',
    options: ['Warm tones','Cool tones','Neutrals','Pastels','Bold & rich','Ivory / White','Black & Dark','No preference'] },
  { id: 'avoid_colour', text: 'Any colours to avoid?', type: 'multi',
    options: ['Black','White','Red','Pink','Gold','Orange','None'] },
  { id: 'fit', text: 'How should the outfit fit you?', type: 'single',
    options: ['Flowy & relaxed','Balanced','Structured & fitted'] },
  { id: 'child_age_group', text: 'How old is the little one?', type: 'single',
    options: ['0-2 years','3-5 years','6-8 years','9-12 years','13-14 years'] },
  { id: 'kidswear_priority', text: 'What matters most to you?', type: 'multi',
    options: ['Super soft fabric','Easy to move in','Easy to wash','Cute look','Special occasion premium'] }
];

export function getNextQuestion(state, answered) {
  if (!answered.includes('gender')) return 'gender';
  if (state.gender === 'My child' && !answered.includes('child_gender')) return 'child_gender';

  const isChild = ['Girl', 'Boy'].includes(state.child_gender);
  if (isChild && !answered.includes('size_kids')) return 'size_kids';
  if (!isChild && !answered.includes('size')) return 'size';

  if (!answered.includes('budget')) return 'budget';
  if (!answered.includes('intent')) return 'intent';
  if (!answered.includes('occasion')) return 'occasion';

  if (state.occasion === 'Wedding / Reception' && !answered.includes('occasion_detail_wedding')) return 'occasion_detail_wedding';
  if (state.occasion === 'Festival / Puja' && !answered.includes('occasion_detail_festival')) return 'occasion_detail_festival';
  if (state.occasion === 'Office / College' && !answered.includes('occasion_detail_office')) return 'occasion_detail_office';

  const kidswear = isChild || (state.intent || []).includes('Kidswear');
  if (kidswear) {
    if (!answered.includes('child_age_group')) return 'child_age_group';
    if (!answered.includes('kidswear_priority')) return 'kidswear_priority';
    return 'RESULTS';
  }

  const exploring = (state.intent || []).includes('Just exploring');
  const casual = state.occasion === 'Casual / Daily wear';

  if (!(casual && exploring) && !answered.includes('style')) return 'style';
  if (!(exploring || casual) && !answered.includes('colour')) return 'colour';

  const needsFit = ['Wedding / Reception', 'Festival / Puja', 'Party / Celebration'].includes(state.occasion);
  if (needsFit && !casual && !answered.includes('fit')) return 'fit';

  return 'RESULTS';
}

// Returns only the question IDs that are actually reachable right now,
// given current state + branch logic — NOT just "everything unanswered."
// This is what gets sent to the LLM for matching, so it can never mistake
// a stray word for a field that isn't even applicable to this session
// (e.g. matching "princess" to child_gender when the user is a grown man).
export function getEligibleQuestions(state, answered) {
  const eligible = [];

  if (!answered.includes('gender')) eligible.push('gender');

  if (state.gender === 'My child' && !answered.includes('child_gender')) {
    eligible.push('child_gender');
  }

  const isChild = ['Girl', 'Boy'].includes(state.child_gender);
  if (state.gender) {
    if (isChild && !answered.includes('size_kids')) eligible.push('size_kids');
    if (!isChild && state.gender !== 'My child' && !answered.includes('size')) eligible.push('size');
  }

  if (!answered.includes('budget')) eligible.push('budget');
  if (!answered.includes('intent')) eligible.push('intent');
  if (!answered.includes('occasion')) eligible.push('occasion');

  if (state.occasion === 'Wedding / Reception' && !answered.includes('occasion_detail_wedding')) {
    eligible.push('occasion_detail_wedding');
  }
  if (state.occasion === 'Festival / Puja' && !answered.includes('occasion_detail_festival')) {
    eligible.push('occasion_detail_festival');
  }
  if (state.occasion === 'Office / College' && !answered.includes('occasion_detail_office')) {
    eligible.push('occasion_detail_office');
  }

  const kidswear = isChild || (state.intent || []).includes('Kidswear');
  if (kidswear) {
    if (!answered.includes('child_age_group')) eligible.push('child_age_group');
    if (!answered.includes('kidswear_priority')) eligible.push('kidswear_priority');
    return eligible; // kidswear branch never reaches style/colour/fit questions below
  }

  const exploring = (state.intent || []).includes('Just exploring');
  const casual = state.occasion === 'Casual / Daily wear';

  if (!(casual && exploring) && !answered.includes('style')) eligible.push('style');
  if (!(exploring || casual) && !answered.includes('colour')) eligible.push('colour');
  if (!(exploring || casual) && !answered.includes('avoid_colour')) eligible.push('avoid_colour');

  const needsFit = ['Wedding / Reception', 'Festival / Puja', 'Party / Celebration'].includes(state.occasion);
  if (needsFit && !casual && !answered.includes('fit')) eligible.push('fit');

  return eligible;
}