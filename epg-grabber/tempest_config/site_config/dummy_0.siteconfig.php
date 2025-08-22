<?php 
/*     Tempest EPG Generator (made by Kvanc)
https://github.com/K-vanc/Tempest-EPG-Generator.git  */
return array (
  'filename' => 'dummy',
  'creator_name' => 'senvora',
  'creation_date' => '2025-01-02',
  'rev_no' => 'R0',
  'timezone' => '+05:30',
  'culture' => 'en',
  'max_day' => '7.1',
  'first_day' => '0123456',
  'compressionOption' => '1',
  'url1' => 'https://github.com/senvora/tvguide/raw/refs/heads/main/epg/dummy.xml.gz',
  'requestOption1' => '1',
  'show' => '<channel id="##channel##" day_no.*?(?:<show>)(.*?)(?:<\\/show>).*?<\\/channel>',
  'start' => '<start>(.*?)<\\/start>',
  'start_format' => 'H:i',
  'stop' => '<stop>(.*?)<\\/stop>',
  'stop_format' => 'H:i',
  'title' => '<title>(.*?)<\\/title>',
  'description' => '<description>(.*?)<\\/description>',
  'channel_logo' => '||#add#https://i.imgur.com/Qlc6VIx.jpg',
  'ccrequestOption1' => '1',
  'ccchannel_id' => '||#set#news|entertainment|movies|sports|infotainment|music|kids|worldwide|livecricket|testchannel|devotional',
  'ccchannel_name' => '||#set#news|entertainment|movies|sports|infotainment|music|kids|worldwide|livecricket|testchannel|devotional',
);
?>