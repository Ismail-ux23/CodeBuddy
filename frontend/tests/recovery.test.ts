// @vitest-environment jsdom
import React from 'react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, act} from '@testing-library/react';
import Upload from '../src/components/workspace/Upload';
import JobStatus from '../src/components/workspace/JobStatus';
const mocks=vi.hoisted(()=>({api:vi.fn(),post:vi.fn(),allPages:vi.fn()}));
vi.mock('../src/lib/api',()=>mocks);
afterEach(()=>{cleanup();vi.clearAllMocks();vi.unstubAllGlobals();});
describe('upload recovery',()=>{
 it('pages a large report and displays source-preview failures',async()=>{
  mocks.post.mockResolvedValue({id:'p'});
  mocks.allPages.mockResolvedValue([{id:'f',relative_path:'main.py',line_count:2}]);
  mocks.api.mockImplementation((path:string)=>path.endsWith('/uploads')
   ? Promise.resolve({id:'s',file_count:1,report:Array.from({length:201},(_,i)=>({path:`ignored/${i}`,reason:'excluded'}))})
   : Promise.reject(new Error('Preview unavailable')));
  const {container}=render(React.createElement(Upload));
  fireEvent.change(screen.getByLabelText('Project name'),{target:{value:'FYP'}});
  fireEvent.change(screen.getByLabelText('Repository ZIP'),{target:{files:[new File(['test'],'repo.zip',{type:'application/zip'})]}});
  fireEvent.click(screen.getByText('Upload & preview'));
  await screen.findByText('Review your source');
  expect(container.querySelectorAll('.report-list li')).toHaveLength(100);
  fireEvent.click(screen.getByText('Next entries'));
  expect(screen.getByText('Page 2 of 3')).toBeTruthy();
  fireEvent.click(screen.getByText('Next entries'));
  expect(container.querySelectorAll('.report-list li')).toHaveLength(1);
  fireEvent.click(screen.getByText('main.py'));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent','Preview unavailable');
 });
});
describe('job recovery',()=>{
 it('clears a transient error when a valid status arrives and handles malformed events',async()=>{
  let onStatus:(event:{data:string})=>void=()=>{};
  const close=vi.fn();
  class Events { onerror:any; addEventListener(_name:string,fn:typeof onStatus){onStatus=fn;} close=close; }
  vi.stubGlobal('EventSource',Events);
  mocks.api.mockRejectedValueOnce(new Error('Temporary network failure'));
  const done=vi.fn();
  render(React.createElement(JobStatus,{id:'j',onDone:done}));
  await screen.findByText('Temporary network failure');
  act(()=>onStatus({data:JSON.stringify({status:'running',stage:'embedding'})}));
  await waitFor(()=>expect(screen.queryByText('Temporary network failure')).toBeNull());
  expect(()=>act(()=>onStatus({data:'not JSON'}))).not.toThrow();
  expect(close).toHaveBeenCalled();
  act(()=>onStatus({data:JSON.stringify({status:'completed',stage:'completed'})}));
  expect(done).toHaveBeenCalledTimes(1);
 });
});
